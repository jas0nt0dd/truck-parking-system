from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import require_gatekeeper_or_admin
from app.db.session import AsyncSessionLocal, get_db
from app.models.billing_rule import BillingRule
from app.models.parking_session import ParkingSession, SessionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.truck import Truck
from app.models.user import User
from app.schemas.session import (
    EntryCreate,
    ExitRequest,
    ExitResponse,
    PaginatedSessions,
    SessionOut,
    SessionSearchItem,
)
from app.services.billing import BillingError, calculate_charge
from app.services.messaging import notify_entry
from app.utils.logging import get_logger
from app.utils.time import duration_hours, utc_now

router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = get_logger(__name__)


async def _send_entry_notification_bg(session_id: uuid.UUID) -> None:
    """Runs in a background task with its own DB session so the entry
    endpoint can return immediately (entry must complete in <=20s)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ParkingSession)
            .options(selectinload(ParkingSession.truck))
            .where(ParkingSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            return
        try:
            await notify_entry(db, session, session.truck)
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Background entry notification failed")
            await db.rollback()


@router.post("/entry", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: EntryCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_gatekeeper_or_admin),
):
    # Find-or-create truck by truck_number (kept simple per beta spec --
    # truck "identity" is informational, sessions are the source of truth).
    result = await db.execute(
        select(Truck).where(Truck.truck_number == payload.truck_number).order_by(Truck.created_at.desc())
    )
    truck = result.scalars().first()

    if truck is None:
        truck = Truck(
            truck_number=payload.truck_number,
            driver_name=payload.driver_name,
            driver_mobile=payload.driver_mobile,
            transport_company=payload.transport_company,
            vehicle_type=payload.vehicle_type,
        )
        db.add(truck)
        await db.flush()
    else:
        # Keep latest driver/company info fresh on repeat visits.
        truck.driver_mobile = payload.driver_mobile
        if payload.driver_name:
            truck.driver_name = payload.driver_name
        if payload.transport_company:
            truck.transport_company = payload.transport_company
        if payload.vehicle_type:
            truck.vehicle_type = payload.vehicle_type

    # Guard: don't allow a duplicate "inside" session for the same truck number.
    existing = await db.execute(
        select(ParkingSession)
        .join(Truck)
        .where(Truck.truck_number == payload.truck_number, ParkingSession.status == SessionStatus.inside)
    )
    if existing.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Truck {payload.truck_number} already has an active session inside the yard",
        )

    session = ParkingSession(
        truck_id=truck.id,
        entry_time=utc_now(),
        entry_photo_url=payload.entry_photo_url,
        remarks=payload.remarks,
        status=SessionStatus.inside,
        gatekeeper_id=current_user.id,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session, attribute_names=["truck"])

    await db.commit()

    if payload.send_notification:
        background_tasks.add_task(_send_entry_notification_bg, session.id)

    return {
        "id": session.id,
        "truck": session.truck,
        "entry_time": session.entry_time,
        "exit_time": session.exit_time,
        "entry_photo_url": session.entry_photo_url,
        "exit_photo_url": session.exit_photo_url,
        "status": session.status,
        "remarks": session.remarks,
        "payment": None,
    }


@router.get("/search", response_model=list[SessionSearchItem])
async def search_sessions(
    q: str = Query(..., min_length=2),
    status_filter: Optional[SessionStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_gatekeeper_or_admin),
):
    query = (
        select(ParkingSession, Truck, Payment)
        .join(Truck, ParkingSession.truck_id == Truck.id)
        .outerjoin(Payment, Payment.session_id == ParkingSession.id)
        .where(
            or_(
                Truck.truck_number.ilike(f"%{q.strip().upper()}%"),
                Truck.driver_mobile.ilike(f"%{q.strip()}%"),
            )
        )
        .order_by(ParkingSession.entry_time.desc())
        .limit(50)
    )
    if status_filter is not None:
        query = query.where(ParkingSession.status == status_filter)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for session, truck, payment in rows:
        dur = (
            duration_hours(session.entry_time, session.exit_time)
            if session.exit_time else duration_hours(session.entry_time, utc_now())
        )
        items.append(
            SessionSearchItem(
                id=session.id,
                truck_number=truck.truck_number,
                driver_mobile=truck.driver_mobile,
                entry_time=session.entry_time,
                exit_time=session.exit_time,
                status=session.status,
                payment_status=payment.payment_status if payment else None,
                duration_hours=dur,
            )
        )
    return items


@router.get("/history", response_model=PaginatedSessions)
async def session_history(
    truck_number: Optional[str] = None,
    driver_mobile: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_gatekeeper_or_admin),
):
    base_query = (
        select(ParkingSession, Truck, Payment)
        .join(Truck, ParkingSession.truck_id == Truck.id)
        .outerjoin(Payment, Payment.session_id == ParkingSession.id)
    )
    filters = []
    if truck_number:
        filters.append(Truck.truck_number.ilike(f"%{truck_number.strip().upper()}%"))
    if driver_mobile:
        filters.append(Truck.driver_mobile.ilike(f"%{driver_mobile.strip()}%"))
    if from_date:
        filters.append(ParkingSession.entry_time >= datetime.combine(from_date, time.min, tzinfo=timezone.utc))
    if to_date:
        filters.append(ParkingSession.entry_time <= datetime.combine(to_date, time.max, tzinfo=timezone.utc))
    if filters:
        base_query = base_query.where(and_(*filters))

    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    paged_query = (
        base_query.order_by(ParkingSession.entry_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(paged_query)).all()

    items = []
    for session, truck, payment in rows:
        dur = (
            duration_hours(session.entry_time, session.exit_time)
            if session.exit_time else duration_hours(session.entry_time, utc_now())
        )
        items.append(
            SessionSearchItem(
                id=session.id,
                truck_number=truck.truck_number,
                driver_mobile=truck.driver_mobile,
                entry_time=session.entry_time,
                exit_time=session.exit_time,
                status=session.status,
                payment_status=payment.payment_status if payment else None,
                duration_hours=dur,
            )
        )

    return PaginatedSessions(items=items, total=total, page=page, page_size=page_size)


@router.post("/{session_id}/exit", response_model=ExitResponse)
async def exit_truck(
    session_id: uuid.UUID,
    payload: ExitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_gatekeeper_or_admin),
):
    result = await db.execute(
        select(ParkingSession)
        .options(selectinload(ParkingSession.truck))
        .where(ParkingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status == SessionStatus.exited:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session already exited")

    session.exit_time = utc_now()
    session.exit_photo_url = payload.exit_photo_url
    session.status = SessionStatus.exited
    session.exit_gatekeeper_id = current_user.id

    dur_hours = duration_hours(session.entry_time, session.exit_time)

    rules_result = await db.execute(select(BillingRule).where(BillingRule.is_active == True))  # noqa: E712
    rules = rules_result.scalars().all()

    try:
        amount, breakdown = calculate_charge(dur_hours, rules)
    except BillingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    payment = Payment(
        session_id=session.id,
        amount=amount,
        payment_status=PaymentStatus.pending,
        billing_breakdown=breakdown,
    )
    db.add(payment)
    await db.flush()
    await db.refresh(session, attribute_names=["payment", "truck"])

    return ExitResponse(
        session=SessionOut.model_validate(session),
        amount_due=amount,
        duration_hours=dur_hours,
        billing_breakdown=breakdown,
    )
