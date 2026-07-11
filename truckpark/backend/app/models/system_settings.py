from __future__ import annotations

from typing import Optional

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class SystemSettings(UUIDPKMixin, TimestampMixin, Base):
    """
    Singleton-style settings table. In practice there should only ever be
    one row; routers enforce get-or-create-first semantics.
    """
    __tablename__ = "system_settings"

    parking_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    company_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    msg91_authkey: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    msg91_sender_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    msg91_whatsapp_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    msg91_entry_template: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    msg91_exit_template: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    notifications_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SystemSettings {self.parking_name}>"
