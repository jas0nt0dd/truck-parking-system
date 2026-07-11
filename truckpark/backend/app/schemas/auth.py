import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import UserRole


class LoginRequest(BaseModel):
    mobile: str = Field(..., min_length=6, max_length=15)
    password: str = Field(..., min_length=4)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    mobile: str
    email: Optional[str] = None
    role: UserRole
    is_active: bool
    is_root: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    mobile: str = Field(..., min_length=6, max_length=15)
    email: Optional[str] = None
    role: UserRole
    password: str = Field(..., min_length=6)

    @field_validator("mobile")
    @classmethod
    def clean_mobile(cls, v: str) -> str:
        return v.strip()

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v):
        if isinstance(v, str):
            value = v.strip()
            return value or None
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v):
        if isinstance(v, str):
            value = v.strip()
            return value or None
        return v


class UserStatusUpdate(BaseModel):
    is_active: bool


class PasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=6)


class PasswordResetResponse(BaseModel):
    message: str
    temporary_password: Optional[str] = None
