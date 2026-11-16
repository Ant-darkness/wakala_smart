from typing import Annotated
from uuid import UUID

from app.db.session import get_db
from app.models.enums import TenantStatus
from app.models.platform_user import PlatformUser
from app.modules.auth.dependencies import get_current_platform_user
from app.modules.platform_admin.admin_schemas import (
    PlatformAdminStatusRequest,
    PlatformAdminStatusResponse,
)
from app.modules.platform_admin.admin_service import (
    update_platform_admin_status,
)
from app.modules.platform_admin.query_schemas import (
    AuditLogListResponse,
    PlatformTenantListResponse,
)
from app.modules.platform_admin.query_service import (
    list_platform_audit_logs,
    list_platform_tenants,
)
from app.modules.platform_admin.schemas import (
    TenantAdminActionResponse,
    TenantStatusUpdateRequest,
)
from app.modules.platform_admin.tenant_service import (
    update_tenant_status,
)
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/platform/admin",
    tags=["Platform Administration"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]

CurrentPlatformAdmin = Annotated[
    PlatformUser,
    Depends(get_current_platform_user),
]


@router.get(
    "/tenants",
    response_model=PlatformTenantListResponse,
)
def get_all_tenants(
    admin: CurrentPlatformAdmin,
    db: DatabaseSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    tenant_status: TenantStatus | None = Query(default=None),
):
    return list_platform_tenants(
        db,
        page=page,
        page_size=page_size,
        search=search,
        tenant_status=tenant_status,
    )


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
)
def get_platform_audit_logs(
    admin: CurrentPlatformAdmin,
    db: DatabaseSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    tenant_id: UUID | None = Query(default=None),
    action: str | None = Query(default=None, max_length=100),
    resource_type: str | None = Query(
        default=None,
        max_length=100,
    ),
):
    return list_platform_audit_logs(
        db,
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
    )


@router.patch(
    "/tenants/{tenant_id}/status",
    response_model=TenantAdminActionResponse,
)
def change_tenant_status(
    tenant_id: UUID,
    data: TenantStatusUpdateRequest,
    request: Request,
    admin: CurrentPlatformAdmin,
    db: DatabaseSession,
):
    return update_tenant_status(
        db,
        admin_id=admin.id,
        tenant_id=tenant_id,
        new_status=data.status,
        reason=data.reason,
        ip_address=(request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
    )


@router.patch(
    "/admins/{admin_id}/status",
    response_model=PlatformAdminStatusResponse,
)
def change_platform_admin_status(
    admin_id: UUID,
    data: PlatformAdminStatusRequest,
    request: Request,
    admin: CurrentPlatformAdmin,
    db: DatabaseSession,
):
    return update_platform_admin_status(
        db,
        current_admin_id=admin.id,
        target_admin_id=admin_id,
        is_active=data.is_active,
        reason=data.reason,
        ip_address=(request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
    )
