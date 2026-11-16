from uuid import UUID

from app.models.audit_log import AuditLog
from sqlalchemy.orm import Session


def record_platform_action(
    db: Session,
    *,
    admin_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID | str,
    tenant_id: UUID | None = None,
    before_data: dict | None = None,
    after_data: dict | None = None,
    reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """
    Record a platform administrator action.

    This function adds the audit record to the current
    database transaction. The caller is responsible for
    committing or rolling back the transaction.
    """

    audit_record = AuditLog(
        actor_platform_user_id=admin_id,
        actor_user_id=None,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        before_data=before_data,
        after_data=after_data,
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(audit_record)

    return audit_record


def record_user_action(
    db: Session,
    *,
    user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID | str,
    tenant_id: UUID | None = None,
    before_data: dict | None = None,
    after_data: dict | None = None,
    reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    audit_record = AuditLog(
        actor_user_id=user_id,
        actor_platform_user_id=None,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        before_data=before_data,
        after_data=after_data,
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(audit_record)
    return audit_record
