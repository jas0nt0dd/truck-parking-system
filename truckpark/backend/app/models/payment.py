from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class PaymentMode(str, enum.Enum):
    cash = "cash"
    upi = "upi"
    credit = "credit"


class PaymentStatus(str, enum.Enum):
    paid = "paid"
    pending = "pending"
    credit = "credit"


class Payment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parking_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_mode: Mapped[Optional[PaymentMode]] = mapped_column(
        Enum(PaymentMode, name="payment_mode", native_enum=True), nullable=True
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=True),
        nullable=False,
        default=PaymentStatus.pending,
        index=True,
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    gatekeeper_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    billing_breakdown: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # JSON breakdown of how the charge was calculated -- useful for audit/dispute resolution

    session = relationship("ParkingSession", back_populates="payment")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Payment {self.id} {self.payment_status}>"
