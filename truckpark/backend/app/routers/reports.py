from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.parking_session import ParkingSession
from app.models.payment import Payment
from app.models.truck import Truck
from app.models.user import User
from app.services.exports import export_sessions_to_excel, export_sessions_to_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/export")
async def export_report(
    from_date: date = Query(...),
    to_date: date = Query(...),
    truck_number: Optional[str] = None,
    driver_mobile: Optional[str] = None,
    format: str = Query("excel", pattern="^(excel|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if to_date < from_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="to_date must be >= from_date")

    start = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(to_date, time.max, tzinfo=timezone.utc)

    query = (
        select(ParkingSession)
        .join(Truck, ParkingSession.truck_id == Truck.id)
        .options(selectinload(ParkingSession.truck), selectinload(ParkingSession.payment))
        .where(ParkingSession.entry_time >= start, ParkingSession.entry_time <= end)
        .order_by(ParkingSession.entry_time.asc())
    )
    if truck_number:
        query = query.where(Truck.truck_number.ilike(f"%{truck_number.strip().upper()}%"))
    if driver_mobile:
        query = query.where(Truck.driver_mobile.ilike(f"%{driver_mobile.strip()}%"))

    sessions = (await db.execute(query)).scalars().all()

    if format == "excel":
        content = export_sessions_to_excel(sessions, from_date, to_date)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"truckpark_report_{from_date}_{to_date}.xlsx"
    else:
        content = export_sessions_to_pdf(sessions, from_date, to_date)
        media_type = "application/pdf"
        filename = f"truckpark_report_{from_date}_{to_date}.pdf"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
