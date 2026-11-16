from datetime import UTC, datetime
from uuid import UUID

from app.models.enums import TenantStatus
from app.models.tenant import Tenant
from app.modules.audit.service import record_platform_action
from app.modules.platform_admin.schemas import TenantAdminAction
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session


def update_tenant_status(
    db: Session,
    *,
    admin_id: UUID,
    tenant_id: UUID,
    new_status: TenantAdminAction,
    reason: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update())

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    old_status = tenant.status

    if old_status == TenantStatus.SOFT_DELETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Soft-deleted tenants cannot be changed.",
        )

    target_status = TenantStatus(new_status.value)

    if old_status == target_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant already has the requested status.",
        )

    tenant.status = target_status

    if target_status == TenantStatus.SOFT_DELETED:
        tenant.deleted_at = datetime.now(UTC)

    record_platform_action(
        db,
        admin_id=admin_id,
        action=f"TENANT_STATUS_CHANGED_{target_status.value}",
        resource_type="TENANT",
        resource_id=tenant.id,
        tenant_id=tenant.id,
        before_data={
            "status": old_status.value,
        },
        after_data={
            "status": target_status.value,
            "deleted_at": (tenant.deleted_at.isoformat() if tenant.deleted_at else None),
        },
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Tenant status updated successfully.",
        "tenant_id": str(tenant.id),
        "previous_status": old_status.value,
        "current_status": target_status.value,
    }
