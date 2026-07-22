from __future__ import annotations

import enum
import uuid
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class UserRole(str, enum.Enum):
    admin = "admin"
    gatekeeper = "gatekeeper"


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    mobile: Mapped[str] = mapped_column(String(15), nullable=False, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_root: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    must_reset_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    gatekeeper_sessions = relationship(
        "ParkingSession", back_populates="gatekeeper", foreign_keys="ParkingSession.gatekeeper_id"
    )
    tenant = relationship("Tenant", back_populates="users")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.mobile} ({self.role})>"
