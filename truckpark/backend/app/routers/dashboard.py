from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, require_gatekeeper_or_admin, tenant_filter
from app.db.session import get_db
from app.models.parking_session import ParkingSession, SessionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.truck import Truck
from app.models.user import User
from app.schemas.dashboard import DashboardSummary, LiveSessionItem
from app.utils.time import duration_hours, utc_now

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _today_bounds_utc() -> tuple[datetime, datetime]:
    now = utc_now()
    start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)
    return start, end


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    start, end = _today_bounds_utc()
    session_scope = tenant_filter(ParkingSession, current_user)
    payment_scope = tenant_filter(Payment, current_user)
    session_filters = [session_scope] if session_scope is not None else []
    payment_filters = [payment_scope] if payment_scope is not None else []

    trucks_inside = (
        await db.execute(
            select(func.count()).select_from(ParkingSession).where(
                ParkingSession.status == SessionStatus.inside, *session_filters
            )
        )
    ).scalar_one()

    entries_today = (
        await db.execute(
            select(func.count()).select_from(ParkingSession).where(
                ParkingSession.entry_time >= start, ParkingSession.entry_time <= end, *session_filters
            )
        )
    ).scalar_one()

    exits_today = (
        await db.execute(
            select(func.count()).select_from(ParkingSession).where(
                ParkingSession.exit_time >= start, ParkingSession.exit_time <= end, *session_filters
            )
        )
    ).scalar_one()

    revenue_today = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.payment_status == PaymentStatus.paid,
                Payment.paid_at >= start,
                Payment.paid_at <= end,
                *payment_filters,
            )
        )
    ).scalar_one()

    pending_payments = (
        await db.execute(
            select(func.count()).select_from(Payment).where(Payment.payment_status == PaymentStatus.pending, *payment_filters)
        )
    ).scalar_one()

    return DashboardSummary(
        trucks_inside=trucks_inside,
        entries_today=entries_today,
        exits_today=exits_today,
        revenue_today=revenue_today,
        pending_payments=pending_payments,
    )


@router.get("/live", response_model=list[LiveSessionItem])
async def dashboard_live(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_gatekeeper_or_admin),
):
    query = (
        select(ParkingSession, Truck, Payment)
        .join(Truck, ParkingSession.truck_id == Truck.id)
        .outerjoin(Payment, Payment.session_id == ParkingSession.id)
        .where(ParkingSession.status == SessionStatus.inside)
        .order_by(ParkingSession.entry_time.asc())
    )
    scope = tenant_filter(ParkingSession, current_user)
    if scope is not None:
        query = query.where(scope)
    rows = (await db.execute(query)).all()

    now = utc_now()
    items = []
    for session, truck, payment in rows:
        items.append(
            LiveSessionItem(
                session_id=str(session.id),
                truck_number=truck.truck_number,
                driver_mobile=truck.driver_mobile,
                entry_time=session.entry_time,
                duration_hours=duration_hours(session.entry_time, now),
                payment_status=payment.payment_status.value if payment else None,
            )
        )
    return items
