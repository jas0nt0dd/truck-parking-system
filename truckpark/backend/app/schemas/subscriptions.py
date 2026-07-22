import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.subscription_request import SubscriptionRequestStatus
from app.models.tenant import SubscriptionStatus, TenantStatus


class SubscriptionRequestCreate(BaseModel):
    parking_name: str = Field(..., min_length=2, max_length=150)
    owner_name: str = Field(..., min_length=2, max_length=120)
    owner_mobile: str = Field(..., min_length=6, max_length=15)
    owner_email: Optional[str] = None
    parking_location: Optional[str] = Field(default=None, max_length=255)
    expected_trucks_per_day: Optional[int] = Field(default=None, ge=0, le=100000)
    message: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("parking_name", "owner_name", "owner_mobile", "parking_location", "message", mode="before")
    @classmethod
    def clean_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("owner_email", mode="before")
    @classmethod
    def clean_email(cls, value):
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value


class SubscriptionRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parking_name: str
    owner_name: str
    owner_mobile: str
    owner_email: Optional[str] = None
    parking_location: Optional[str] = None
    expected_trucks_per_day: Optional[int] = None
    message: Optional[str] = None
    status: SubscriptionRequestStatus
    admin_notes: Optional[str] = None
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    tenant_id: Optional[uuid.UUID] = None


class SubscriptionRequestDecision(BaseModel):
    admin_notes: Optional[str] = Field(default=None, max_length=2000)
    plan_name: str = Field(default="manual", min_length=2, max_length=80)
    subscription_expires_at: Optional[datetime] = None
    database_name: Optional[str] = Field(default=None, max_length=120)
    database_url: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("admin_notes", "plan_name", "database_name", "database_url", mode="before")
    @classmethod
    def clean_optional_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    owner_name: str
    owner_mobile: str
    owner_email: Optional[str] = None
    parking_location: Optional[str] = None
    status: TenantStatus
    subscription_status: SubscriptionStatus
    plan_name: str
    database_name: Optional[str] = None
    subscription_started_at: Optional[datetime] = None
    subscription_expires_at: Optional[datetime] = None
    created_at: datetime


class SubscriptionApprovalOut(BaseModel):
    request: SubscriptionRequestOut
    tenant: TenantOut
    owner_mobile: str
    temporary_password: str
