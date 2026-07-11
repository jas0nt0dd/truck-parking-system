from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin


class Truck(UUIDPKMixin, Base):
    __tablename__ = "trucks"

    truck_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    driver_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    driver_mobile: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    transport_company: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    vehicle_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sessions = relationship("ParkingSession", back_populates="truck")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Truck {self.truck_number}>"
