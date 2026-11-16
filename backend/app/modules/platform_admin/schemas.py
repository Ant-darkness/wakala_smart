from enum import StrEnum

from pydantic import BaseModel, Field


class TenantAdminAction(StrEnum):
    ACTIVATE = "ACTIVE"
    RESTRICT = "RESTRICTED"
    LOCK = "LOCKED"
    SOFT_DELETE = "SOFT_DELETED"


class TenantStatusUpdateRequest(BaseModel):
    status: TenantAdminAction
    reason: str = Field(min_length=10, max_length=500)


class TenantAdminActionResponse(BaseModel):
    message: str
    tenant_id: str
    previous_status: str
    current_status: str
