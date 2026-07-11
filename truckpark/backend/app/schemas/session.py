import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.parking_session import SessionStatus
from app.models.payment import PaymentMode, PaymentStatus


class TruckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    truck_number: str
    driver_name: Optional[str] = None
    driver_mobile: str
    transport_company: Optional[str] = None
    vehicle_type: Optional[str] = None


class EntryCreate(BaseModel):
    truck_number: str = Field(..., min_length=2, max_length=20)
    driver_mobile: str = Field(..., min_length=6, max_length=15)
    driver_name: Optional[str] = Field(None, max_length=120)
    transport_company: Optional[str] = Field(None, max_length=150)
    vehicle_type: Optional[str] = Field(None, max_length=50)
    remarks: Optional[str] = None
    entry_photo_url: Optional[str] = None
    send_notification: bool = True

    @field_validator("truck_number")
    @classmethod
    def upper_truck_number(cls, v: str) -> str:
        return v.strip().upper().replace(" ", "")

    @field_validator("driver_mobile")
    @classmethod
    def clean_mobile(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 10:
            raise ValueError("driver_mobile must contain at least 10 digits")
        return digits[-10:]


class ExitRequest(BaseModel):
    exit_photo_url: Optional[str] = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    payment_mode: Optional[PaymentMode] = None
    payment_status: PaymentStatus
    paid_at: Optional[datetime] = None
    billing_breakdown: Optional[list] = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    truck: TruckOut
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_photo_url: Optional[str] = None
    exit_photo_url: Optional[str] = None
    status: SessionStatus
    remarks: Optional[str] = None
    payment: Optional[PaymentOut] = None


class ExitResponse(BaseModel):
    session: SessionOut
    amount_due: Decimal
    duration_hours: float
    billing_breakdown: list


class MarkPaidRequest(BaseModel):
    payment_mode: PaymentMode
    amount: Optional[Decimal] = None
    send_notification: bool = True


class SessionSearchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    truck_number: str
    driver_mobile: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    status: SessionStatus
    payment_status: Optional[PaymentStatus] = None
    duration_hours: Optional[float] = None


class PaginatedSessions(BaseModel):
    items: list[SessionSearchItem]
    total: int
    page: int
    page_size: int
