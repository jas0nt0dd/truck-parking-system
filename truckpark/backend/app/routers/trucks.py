from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import require_gatekeeper_or_admin
from app.db.session import get_db
from app.models.parking_session import ParkingSession
from app.models.truck import Truck
from app.models.user import User
from app.schemas.session import SessionOut, TruckOut

router = APIRouter(prefix="/trucks", tags=["trucks"])


@router.get("/{truck_number}/history", response_model=list[SessionOut])
async def truck_history(
    truck_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_gatekeeper_or_admin),
):
    """Complete visit history for a single truck, identified by truck number."""
    result = await db.execute(
        select(ParkingSession)
        .join(Truck, ParkingSession.truck_id == Truck.id)
        .options(selectinload(ParkingSession.truck), selectinload(ParkingSession.payment))
        .where(Truck.truck_number == truck_number.strip().upper())
        .order_by(ParkingSession.entry_time.desc())
    )
    sessions = result.scalars().all()
    return sessions
