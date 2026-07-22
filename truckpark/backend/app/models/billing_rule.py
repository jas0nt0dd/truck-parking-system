from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class BillingRule(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "billing_rules"

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rule_name: Mapped[str] = mapped_column(String(120), nullable=False)
    from_hours: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    to_hours: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    charge: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BillingRule {self.rule_name}>"
