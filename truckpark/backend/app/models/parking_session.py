from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class SessionStatus(str, enum.Enum):
    inside = "inside"
    exited = "exited"


class ParkingSession(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "parking_sessions"

    truck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trucks.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    entry_photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    exit_photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status", native_enum=True),
        default=SessionStatus.inside,
        nullable=False,
        index=True,
    )
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gatekeeper_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    exit_gatekeeper_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    truck = relationship("Truck", back_populates="sessions")
    gatekeeper = relationship("User", back_populates="gatekeeper_sessions", foreign_keys=[gatekeeper_id])
    payment = relationship("Payment", back_populates="session", uselist=False)
    notifications = relationship("Notification", back_populates="session")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ParkingSession {self.id} status={self.status}>"
