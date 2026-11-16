from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    price: Decimal
    currency: str
    billing_interval: str
    limits: dict
    features: dict
    is_active: bool


class PlanCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="TZS", min_length=3, max_length=3)
    billing_interval: str = Field(default="MONTHLY")
    limits: dict = Field(default_factory=dict)
    features: dict = Field(default_factory=dict)


class PlanUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    limits: dict | None = None
    features: dict | None = None
    is_active: bool | None = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plan_id: UUID
    status: str
    starts_at: datetime
    ends_at: datetime | None
    trial_ends_at: datetime | None
    cancelled_at: datetime | None


class AssignSubscriptionRequest(BaseModel):
    plan_id: UUID
    status: str = "ACTIVE"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    trial_ends_at: datetime | None = None


class PlatformSubscriptionItem(SubscriptionResponse):
    tenant_name: str
    plan_name: str


class PlatformSubscriptionListResponse(BaseModel):
    items: list[PlatformSubscriptionItem]
    total: int
    page: int
    page_size: int
