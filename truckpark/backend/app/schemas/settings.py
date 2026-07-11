import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SystemSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parking_name: Optional[str] = None
    logo_url: Optional[str] = None
    msg91_sender_id: Optional[str] = None
    msg91_whatsapp_number: Optional[str] = None
    msg91_entry_template: Optional[str] = None
    msg91_exit_template: Optional[str] = None
    notifications_enabled: bool


class SystemSettingsUpdate(BaseModel):
    parking_name: Optional[str] = None
    logo_url: Optional[str] = None
    msg91_authkey: Optional[str] = None
    msg91_sender_id: Optional[str] = None
    msg91_whatsapp_number: Optional[str] = None
    msg91_entry_template: Optional[str] = None
    msg91_exit_template: Optional[str] = None
    notifications_enabled: Optional[bool] = None
