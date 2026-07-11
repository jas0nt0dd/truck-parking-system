"""
Time helpers. All persisted timestamps are UTC (tz-aware). Conversion
to IST (Asia/Kolkata) for display is the frontend's job per the spec,
but we expose a helper here too for server-rendered exports (Excel/PDF).
"""
from datetime import datetime, timezone

import pytz

from app.core.config import settings

DISPLAY_TZ = pytz.timezone(settings.DISPLAY_TIMEZONE)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_display_tz(dt: datetime) -> datetime:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(DISPLAY_TZ)


def duration_hours(start: datetime, end: datetime) -> float:
    """Returns duration in hours (float) between two tz-aware datetimes."""
    delta = end - start
    return round(delta.total_seconds() / 3600, 4)


def format_duration(hours: float) -> str:
    total_minutes = int(round(hours * 60))
    h, m = divmod(total_minutes, 60)
    days, h = divmod(h, 24)
    parts = []
    if days:
        parts.append(f"{days}d")
    if h or days:
        parts.append(f"{h}h")
    parts.append(f"{m}m")
    return " ".join(parts)
