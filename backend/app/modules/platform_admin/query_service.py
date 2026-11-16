from app.models.audit_log import AuditLog
from app.models.enums import TenantStatus
from app.models.tenant import Tenant
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def list_platform_tenants(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    tenant_status: TenantStatus | None = None,
) -> dict:
    filters = [Tenant.deleted_at.is_(None)]

    if search:
        term = f"%{search.strip()}%"
        filters.append((Tenant.name.ilike(term)) | (Tenant.slug.ilike(term)))

    if tenant_status is not None:
        filters.append(Tenant.status == tenant_status)

    total = db.scalar(select(func.count(Tenant.id)).where(*filters)) or 0

    items = db.scalars(
        select(Tenant)
        .where(*filters)
        .order_by(Tenant.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def list_platform_audit_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    tenant_id=None,
    action: str | None = None,
    resource_type: str | None = None,
) -> dict:
    filters = []

    if tenant_id is not None:
        filters.append(AuditLog.tenant_id == tenant_id)

    if action:
        filters.append(AuditLog.action == action)

    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)

    total = db.scalar(select(func.count(AuditLog.id)).where(*filters)) or 0

    items = db.scalars(
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
