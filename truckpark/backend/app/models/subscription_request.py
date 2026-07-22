from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin


class SubscriptionRequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class SubscriptionRequest(UUIDPKMixin, Base):
    __tablename__ = "subscription_requests"

    parking_name: Mapped[str] = mapped_column(String(150), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_mobile: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parking_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expected_trucks_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[SubscriptionRequestStatus] = mapped_column(
        Enum(SubscriptionRequestStatus, name="subscription_request_status", native_enum=True),
        default=SubscriptionRequestStatus.pending,
        nullable=False,
        index=True,
    )
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )

    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    tenant = relationship("Tenant", back_populates="subscription_requests")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SubscriptionRequest {self.parking_name} ({self.status})>"
