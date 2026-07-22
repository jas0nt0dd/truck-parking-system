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
                 entry_template: str, exit_template: str, enabled: bool,
                 parking_name: str):
        self.authkey = authkey
        self.sender_id = sender_id
        self.whatsapp_number = whatsapp_number
        self.entry_template = entry_template
        self.exit_template = exit_template
        self.enabled = enabled
        self.parking_name = parking_name

    @property
    def is_configured(self) -> bool:
        return bool(self.authkey and self.whatsapp_number)


async def load_msg91_config(db: AsyncSession, tenant_id: Optional[uuid.UUID] = None) -> MSG91Config:
    result = await db.execute(select(SystemSettings).where(SystemSettings.tenant_id == tenant_id).limit(1))
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
        parking_name=(row.parking_name if row and row.parking_name else settings.APP_NAME),
    )


class MSG91WhatsAppProvider:
    """Thin client around MSG91's WhatsApp template-send endpoint."""

    def __init__(self, config: MSG91Config):
        self.config = config

    @staticmethod
    def _normalize_phone_number(number: str) -> str:
        value = str(number or "").strip()
        if not value:
            return value
        if value.startswith("+"):
            return value
        if value.startswith("00"):
            return f"+{value[2:]}"
        if value.isdigit():
            if value.startswith("0") and len(value) == 10:
                return f"+91{value[1:]}"
            if len(value) == 10:
                return f"+91{value}"
            return f"+{value}"
        return value

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def _send(self, template_name: str, mobile: str, variables: tuple | list | dict) -> dict:
        if not self.config.is_configured:
            raise RuntimeError("MSG91 is not configured (missing authkey/whatsapp number)")

        if isinstance(variables, dict):
            ordered_values = list(variables.values())
        else:
            ordered_values = list(variables)

        base_url = settings.MSG91_BASE_URL.rstrip("/")
        url = f"{base_url}/whatsapp/whatsapp-outbound-message/bulk/"
        components = {
            f"body_{i+1}": {"type": "text", "value": str(v)}
            for i, v in enumerate(ordered_values)
        }
        normalized_mobile = self._normalize_phone_number(mobile)
        normalized_whatsapp_number = self._normalize_phone_number(self.config.whatsapp_number)
        payload = {
            "integrated_number": normalized_whatsapp_number,
            "content_type": "template",
            "payload": {
                "messaging_product": "whatsapp",
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en", "policy": "deterministic"},
                    "to_and_components": [{"to": [normalized_mobile], "components": components}],
                },
            },
        }
        headers = {
            "accept": "application/json",
            "authkey": self.config.authkey,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", errors="replace")
                raise httpx.HTTPStatusError(
                    f"MSG91 request failed with status {resp.status_code}: {body}",
                    request=resp.request,
                    response=resp,
                )
            return resp.json()

    async def send_entry_message(
        self, mobile: str, truck_number: str, parking_name: str,
        entry_time_str: str, driver_mobile: str,
    ) -> dict:
        variables = (
            truck_number,
            parking_name,
            entry_time_str,
            driver_mobile,
        )
        return await self._send(self.config.entry_template, mobile, variables)

    async def send_exit_message(
        self, mobile: str, truck_number: str, parking_name: str,
        entry_time_str: str, exit_time_str: str, duration_str: str,
        amount: Decimal, payment_mode: str,
    ) -> dict:
        variables = (
            truck_number,
            parking_name,
            entry_time_str,
            exit_time_str,
            duration_str,
            str(amount),
            payment_mode,
        )
        return await self._send(self.config.exit_template, mobile, variables)


async def _record_notification(
    db: AsyncSession, session_id: Optional[uuid.UUID], mobile: str,
    message_type: NotificationType, status: NotificationStatus, error: Optional[str] = None,
    tenant_id: Optional[uuid.UUID] = None,
) -> Notification:
    notif = Notification(
        tenant_id=tenant_id,
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
    config = await load_msg91_config(db, session.tenant_id)
    if not config.enabled:
        logger.info("Notifications disabled in system settings; skipping entry notification")
        return
    if not config.is_configured:
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.entry,
            NotificationStatus.failed, error="MSG91 not configured", tenant_id=session.tenant_id,
        )
        return
    try:
        provider = MSG91WhatsAppProvider(config)
        entry_time_str = to_display_tz(session.entry_time).strftime("%d-%b-%Y %I:%M %p")
        parking_name = config.parking_name or settings.APP_NAME
        await provider.send_entry_message(
            truck.driver_mobile,
            truck.truck_number,
            parking_name,
            entry_time_str,
            truck.driver_mobile,
        )
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.entry,
            NotificationStatus.sent, tenant_id=session.tenant_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("MSG91 entry notification failed: %s", exc)
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.entry,
            NotificationStatus.failed, error=str(exc), tenant_id=session.tenant_id,
        )


async def notify_exit(
    db: AsyncSession, session: ParkingSession, truck: Truck, amount: Decimal, payment_mode: str
) -> None:
    if session.exit_time is None:
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.exit,
            NotificationStatus.failed,
            error="Cannot send exit receipt before exit_time is set",
            tenant_id=session.tenant_id,
        )
        return

    config = await load_msg91_config(db, session.tenant_id)
    if not config.enabled:
        logger.info("Notifications disabled in system settings; skipping exit notification")
        return
    if not config.is_configured:
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.exit,
            NotificationStatus.failed, error="MSG91 not configured", tenant_id=session.tenant_id,
        )
        return
    try:
        provider = MSG91WhatsAppProvider(config)
        entry_time_str = to_display_tz(session.entry_time).strftime("%d-%b-%Y %I:%M %p")
        exit_time_str = to_display_tz(session.exit_time).strftime("%d-%b-%Y %I:%M %p")
        dur_str = format_duration(duration_hours(session.entry_time, session.exit_time))
        parking_name = config.parking_name or settings.APP_NAME
        await provider.send_exit_message(
            truck.driver_mobile,
            truck.truck_number,
            parking_name,
            entry_time_str,
            exit_time_str,
            dur_str,
            amount,
            payment_mode,
        )
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.exit,
            NotificationStatus.sent, tenant_id=session.tenant_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("MSG91 exit notification failed: %s", exc)
        await _record_notification(
            db, session.id, truck.driver_mobile, NotificationType.exit,
            NotificationStatus.failed, error=str(exc), tenant_id=session.tenant_id,
        )
