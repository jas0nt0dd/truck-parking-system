import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BillingRuleBase(BaseModel):
    rule_name: str = Field(..., min_length=2, max_length=120)
    from_hours: Decimal = Field(..., ge=0)
    to_hours: Optional[Decimal] = Field(None, ge=0)
    charge: Decimal = Field(..., ge=0)
    priority: int = Field(1, ge=1)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_range(self):
        if self.to_hours is not None and self.to_hours <= self.from_hours:
            raise ValueError("to_hours must be greater than from_hours")
        return self


class BillingRuleCreate(BillingRuleBase):
    pass


class BillingRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    from_hours: Optional[Decimal] = None
    to_hours: Optional[Decimal] = None
    charge: Optional[Decimal] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class BillingRuleOut(BillingRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
