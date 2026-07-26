import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import require_gatekeeper_or_admin, require_same_tenant, tenant_filter
from app.db.session import AsyncSessionLocal, get_db
from app.models.parking_session import ParkingSession, SessionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.schemas.session import MarkPaidRequest, SessionOut
from app.services.exports import export_session_bill_to_pdf
from app.services.messaging import notify_exit, notify_pending_bill
from app.utils.logging import get_logger
from app.utils.time import utc_now

router = APIRouter(prefix="/payments", tags=["payments"])
logger = get_logger(__name__)


async def _send_exit_notification_bg(session_id: uuid.UUID, amount, payment_mode: str, bill_url: str) -> None:
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
            logger.info(
                "Sending background exit WhatsApp for session %s with bill URL %s",
                session_id,
                bill_url,
            )
            await notify_exit(db, session, session.truck, amount, payment_mode, bill_url)
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Background exit notification failed")
            await db.rollback()


async def _send_bill_notification_bg(session_id: uuid.UUID, bill_url: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ParkingSession)
            .options(selectinload(ParkingSession.truck), selectinload(ParkingSession.payment))
            .where(ParkingSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is None or session.payment is None:
            return
        try:
            if session.payment.payment_status == PaymentStatus.paid:
                payment_mode = session.payment.payment_mode.value if session.payment.payment_mode else "Paid"
                logger.info(
                    "Background bill notification: paid exit for session %s, sending WhatsApp template %s",
                    session.id,
                    config.exit_template,
                )
                await notify_exit(db, session, session.truck, session.payment.amount, payment_mode, bill_url)
            else:
                logger.info(
                    "Background bill notification: pending exit for session %s, sending bill URL %s",
                    session.id,
                    bill_url,
                )
                await notify_pending_bill(db, session, session.truck, bill_url)
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Background bill notification failed")
            await db.rollback()


@router.post("/{session_id}/mark-paid", response_model=SessionOut)
async def mark_paid(
    session_id: uuid.UUID,
    payload: MarkPaidRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_gatekeeper_or_admin),
):
    result = await db.execute(
        select(Payment).where(
            Payment.session_id == session_id,
            *([tenant_filter(Payment, current_user)] if tenant_filter(Payment, current_user) is not None else []),
        )
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found for this session")
    if payment.payment_status == PaymentStatus.paid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment already marked as paid")

    payment.payment_mode = payload.payment_mode
    if payload.amount is not None:
        payment.amount = payload.amount
    payment.payment_status = PaymentStatus.paid
    payment.paid_at = utc_now()
    payment.gatekeeper_id = current_user.id

    session_result = await db.execute(
        select(ParkingSession)
        .options(selectinload(ParkingSession.truck), selectinload(ParkingSession.payment))
        .where(ParkingSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    require_same_tenant(session, current_user)

    await db.flush()
    await db.refresh(session, attribute_names=["payment", "truck"])

    await db.commit()

    if payload.send_notification:
        bill_url = request.url_for("payment_bill", session_id=str(session.id))
        background_tasks.add_task(_send_bill_notification_bg, session.id, bill_url)

    return SessionOut.model_validate(session)


@router.post("/{session_id}/send-bill", response_model=SessionOut)
async def send_bill_link(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_gatekeeper_or_admin),
):
    result = await db.execute(
        select(ParkingSession)
        .options(selectinload(ParkingSession.truck), selectinload(ParkingSession.payment))
        .where(ParkingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    require_same_tenant(session, current_user)
    if session.payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found for this session")
    if session.status != SessionStatus.exited:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only send bill for exited sessions")

    bill_url = request.url_for("payment_bill", session_id=str(session.id))
    background_tasks.add_task(_send_bill_notification_bg, session.id, bill_url)

    return SessionOut.model_validate(session)


@router.get("/{session_id}/bill", name="payment_bill")
async def download_bill(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ParkingSession)
        .options(selectinload(ParkingSession.truck), selectinload(ParkingSession.payment))
        .where(ParkingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None or session.payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    if session.status != SessionStatus.exited:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill available only for exited sessions")

    content = export_session_bill_to_pdf(session)
    filename = f"truckpark_bill_{session.truck.truck_number}_{session.id}.pdf"
    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
