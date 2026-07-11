from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    trucks_inside: int
    entries_today: int
    exits_today: int
    revenue_today: Decimal
    pending_payments: int


class LiveSessionItem(BaseModel):
    session_id: str
    truck_number: str
    driver_mobile: str
    entry_time: datetime
    duration_hours: float
    payment_status: Optional[str] = None


class ReportQuery(BaseModel):
    from_date: date
    to_date: date
    truck_number: Optional[str] = None
    driver_mobile: Optional[str] = None
    format: str = "excel"  # excel | pdf
