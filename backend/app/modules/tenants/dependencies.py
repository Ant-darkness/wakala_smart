from typing import Annotated
from uuid import UUID

from app.db.session import get_db
from app.models.enums import MembershipStatus, TenantStatus
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.tenant import Tenant
from app.models.tenant_member import TenantMember
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_current_tenant_member(
    tenant_id: Annotated[UUID, Header(alias="X-Tenant-ID")],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TenantMember:
    tenant = db.scalar(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.status == TenantStatus.ACTIVE,
            Tenant.deleted_at.is_(None),
        )
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found or unavailable.",
        )

    membership = db.scalar(
        select(TenantMember).where(
            TenantMember.tenant_id == tenant_id,
            TenantMember.user_id == user.id,
            TenantMember.status == MembershipStatus.ACTIVE,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an active member of this business.",
        )

    return membership


def require_permission(permission_code: str):
    def permission_dependency(
        membership: Annotated[
            TenantMember,
            Depends(get_current_tenant_member),
        ],
        db: Annotated[Session, Depends(get_db)],
    ) -> TenantMember:
        has_permission = db.scalar(
            select(Permission.id)
            .join(
                RolePermission,
                RolePermission.permission_id == Permission.id,
            )
            .join(
                Role,
                Role.id == RolePermission.role_id,
            )
            .where(
                Role.id == membership.role_id,
                Role.tenant_id == membership.tenant_id,
                Permission.code == permission_code,
            )
        )

        if has_permission is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return membership

    return permission_dependency
