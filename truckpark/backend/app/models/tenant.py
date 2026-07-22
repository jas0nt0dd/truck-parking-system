from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class TenantStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"
    cancelled = "cancelled"


class SubscriptionStatus(str, enum.Enum):
    trial = "trial"
    active = "active"
    past_due = "past_due"
    cancelled = "cancelled"


class Tenant(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_mobile: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parking_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, name="tenant_status", native_enum=True),
        nullable=False,
        default=TenantStatus.active,
        index=True,
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status", native_enum=True),
        nullable=False,
        default=SubscriptionStatus.active,
        index=True,
    )
    plan_name: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    database_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    database_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subscription_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    users = relationship("User", back_populates="tenant")
    subscription_requests = relationship("SubscriptionRequest", back_populates="tenant")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tenant {self.slug} ({self.status})>"
