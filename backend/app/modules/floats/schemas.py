from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.float_alert_enums import FloatAlertStatus
from pydantic import BaseModel, ConfigDict, Field


class FloatAlertSettingUpsertRequest(BaseModel):
    account_id: UUID
    minimum_balance: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    is_enabled: bool = True


class FloatAlertSettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    account_id: UUID
    minimum_balance: Decimal
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class FloatAlertEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    account_id: UUID
    minimum_balance: Decimal
    observed_balance: Decimal
    status: FloatAlertStatus
    message: str
    created_at: datetime
    resolved_at: datetime | None


class FloatAlertEventListResponse(BaseModel):
    items: list[FloatAlertEventResponse]
    total: int
    page: int
    page_size: int
