import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import require_gatekeeper_or_admin
from app.db.session import AsyncSessionLocal, get_db
from app.models.parking_session import ParkingSession
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.schemas.session import MarkPaidRequest, SessionOut
from app.services.messaging import notify_exit
from app.utils.logging import get_logger
from app.utils.time import utc_now

router = APIRouter(prefix="/payments", tags=["payments"])
logger = get_logger(__name__)


async def _send_exit_notification_bg(session_id: uuid.UUID, amount, payment_mode: str) -> None:
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
            await notify_exit(db, session, session.truck, amount, payment_mode)
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Background exit notification failed")
            await db.rollback()


@router.post("/{session_id}/mark-paid", response_model=SessionOut)
async def mark_paid(
    session_id: uuid.UUID,
    payload: MarkPaidRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_gatekeeper_or_admin),
):
    result = await db.execute(
        select(Payment).where(Payment.session_id == session_id)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found for this session")
    if payment.payment_status == PaymentStatus.paid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment already marked as paid")

    payment.payment_mode = payload.payment_mode
    if payload.amount is not None:
        payment.amount = payload.amount
    payment.payment_status = (
        PaymentStatus.credit if payload.payment_mode == "credit" else PaymentStatus.paid
    )
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

    await db.flush()
    await db.refresh(session, attribute_names=["payment", "truck"])

    if payload.send_notification:
        background_tasks.add_task(
            _send_exit_notification_bg, session.id, payment.amount, payment.payment_mode.value
        )

    return SessionOut.model_validate(session)
