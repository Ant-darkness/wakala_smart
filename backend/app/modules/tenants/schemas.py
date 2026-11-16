import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: str
    created_at: datetime


class TenantListResponse(BaseModel):
    items: list[TenantResponse]
    total: int
