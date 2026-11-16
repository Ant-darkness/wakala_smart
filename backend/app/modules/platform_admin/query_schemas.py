from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlatformTenantItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    status: str
    created_at: datetime


class PlatformTenantListResponse(BaseModel):
    items: list[PlatformTenantItem]
    total: int
    page: int
    page_size: int


class AuditLogItem(BaseModel):
    id: UUID
    actor_platform_user_id: UUID | None
    actor_user_id: UUID | None
    tenant_id: UUID | None
    action: str
    resource_type: str
    resource_id: str
    before_data: dict | None
    after_data: dict | None
    reason: str | None
    ip_address: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int
