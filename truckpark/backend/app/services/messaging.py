"""
MSG91 WhatsApp Business API integration.

Sends template-based WhatsApp messages for truck entry notifications
and exit/payment receipts. Credentials are loaded from SystemSettings
(DB, admin-configurable) with a fallback to environment variables so
the app still works before an admin has configured anything via the UI.

Every send attempt is recorded in the `notifications` table regardless
of success/failure, satisfying the audit requirement in the spec.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.notification import Notification, NotificationStatus, NotificationType
from app.models.parking_session import ParkingSession
from app.models.system_settings import SystemSettings
from app.models.truck import Truck
from app.utils.logging import get_logger
from app.utils.time import duration_hours, format_duration, to_display_tz

logger = get_logger(__name__)


class MSG91Config:
    def __init__(self, authkey: str, sender_id: str, whatsapp_number: str,
                 entry_template: str, exit_template: str, enabled: bool):
        self.authkey = authkey
        self.sender_id = sender_id
        self.whatsapp_number = whatsapp_number
        self.entry_template = entry_template
        self.exit_template = exit_template
        self.enabled = enabled

    @property
    def is_configured(self) -> bool:
        return bool(self.authkey and self.whatsapp_number)


async def load_msg91_config(db: AsyncSession) -> MSG91Config:
    result = await db.execute(select(SystemSettings).limit(1))
    row = result.scalar_one_or_none()
    return MSG91Config(
        authkey=(row.msg91_authkey if row and row.msg91_authkey else settings.MSG91_AUTHKEY),
        sender_id=(row.msg91_sender_id if row and row.msg91_sender_id else settings.MSG91_SENDER_ID),
        whatsapp_number=(
            row.msg91_whatsapp_number if row and row.msg91_whatsapp_number
            else settings.MSG91_WHATSAPP_NUMBER
        ),
        entry_template=(
            row.msg91_entry_template if row and row.msg91_entry_template
            else settings.MSG91_ENTRY_TEMPLATE_NAME
        ),
        exit_template=(
            row.msg91_exit_template if row and row.msg91_exit_template
            else settings.MSG91_EXIT_TEMPLATE_NAME
        ),
        enabled=(row.notifications_enabled if row else True),
    )


class MSG91WhatsAppProvider:
    """Thin client around MSG91's WhatsApp template-send endpoint."""

    def __init__(self, config: MSG91Config):
        self.config = config

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def _send(self, template_name: str, mobile: str, variables: dict) -> dict:
        if not self.config.is_configured:
            raise RuntimeError("MSG91 is not configured (missing authkey/whatsapp number)")

        url = f"{settings.MSG91_BASE_URL}/whatsapp/whatsapp-outbound-message/bulk/"
        components = {
            f"body_{i+1}": {"type": "text", "value": str(v)}
            for i, v in enumerate(variables.values())
        }
        payload = {
            "integrated_number": self.config.whatsapp_number,
            "content_type": "template",
            "payload": {
                "messaging_product": "whatsapp",
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en", "policy": "deterministic"},
                    "to_and_components": [{"to": [mobile], "components": components}],
                },
            },
        }
        headers = {"authkey": self.config.authkey, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def send_entry_message(self, mobile: str, truck_number: str, entry_time_str: str) -> dict:
        variables = {"truck_number": truck_number, "entry_time": entry_time_str}
        return await self._send(self.config.entry_template, mobile, variables)

    async def send_exit_message(
        self, mobile: str, truck_number: str, entry_time_str: str, exit_time_str: str,
        duration_str: str, amount: Decimal, payment_mode: str,
    ) -> dict:
        variables = {
            "truck_number": truck_number,
            "entry_time": entry_time_str,
            "exit_time": exit_time_str,
            "duration": duration_str,
            "amount": str(amount),
            "payment_mode": payment_mode,
        }
        return await self._send(self.config.exit_template, mobile, variables)


async def _record_notification(
    db: AsyncSession, session_id: Optional[uuid.UUID], mobile: str,
    message_type: NotificationType, status: NotificationStatus, error: Optional[str] = None,
) -> Notification:
    notif = Notification(
        session_id=session_id,
        mobile=mobile,
        channel="whatsapp",
        message_type=message_type,
        status=status,
        attempts=1,
        error_message=error,
    )
    from app.utils.time import utc_now
    notif.last_attempted_at = utc_now()
    db.add(notif)
    await db.flush()
    return notif


async def notify_entry(db: AsyncSession, session: ParkingSession, truck: Truck) -> None:
    """Best-effort: failures are logged + recorded, never raised to caller."""
    config = await load_msg91_config(db)
    if not config.enabled:
        logger.info("Notifications disabled in system settings; skipping entry notification")
        return
    if not config.is_configured:
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.entry,
            NotificationStatus.failed, error="MSG91 not configured",
        )
        return
    try:
        provider = MSG91WhatsAppProvider(config)
        entry_time_str = to_display_tz(session.entry_time).strftime("%d-%b-%Y %I:%M %p")
        await provider.send_entry_message(truck.driver_mobile, truck.truck_number, entry_time_str)
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.entry, NotificationStatus.sent
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("MSG91 entry notification failed: %s", exc)
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.entry,
            NotificationStatus.failed, error=str(exc),
        )


async def notify_exit(
    db: AsyncSession, session: ParkingSession, truck: Truck, amount: Decimal, payment_mode: str
) -> None:
    config = await load_msg91_config(db)
    if not config.enabled:
        logger.info("Notifications disabled in system settings; skipping exit notification")
        return
    if not config.is_configured:
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.exit,
            NotificationStatus.failed, error="MSG91 not configured",
        )
        return
    try:
        provider = MSG91WhatsAppProvider(config)
        entry_time_str = to_display_tz(session.entry_time).strftime("%d-%b-%Y %I:%M %p")
        exit_time_str = to_display_tz(session.exit_time).strftime("%d-%b-%Y %I:%M %p")
        dur_str = format_duration(duration_hours(session.entry_time, session.exit_time))
        await provider.send_exit_message(
            truck.driver_mobile, truck.truck_number, entry_time_str, exit_time_str,
            dur_str, amount, payment_mode,
        )
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.exit, NotificationStatus.sent
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("MSG91 exit notification failed: %s", exc)
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.exit,
            NotificationStatus.failed, error=str(exc),
        )
