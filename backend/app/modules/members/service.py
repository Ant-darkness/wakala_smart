from app.models.enums import MembershipStatus, RoleCode, UserStatus
from app.models.role import Role
from app.models.tenant_member import TenantMember
from app.models.user import User
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session


def add_agent(
    db: Session,
    tenant_member: TenantMember,
    email: str,
) -> TenantMember:
    normalized_email = email.strip().lower()

    agent = db.scalar(select(User).where(User.email == normalized_email))

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered user found with this email.",
        )

    if agent.status != UserStatus.ACTIVE or not agent.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected user is not eligible for membership.",
        )

    existing_membership = db.scalar(
        select(TenantMember).where(
            TenantMember.tenant_id == tenant_member.tenant_id,
            TenantMember.user_id == agent.id,
        )
    )

    if existing_membership is not None:
        if existing_membership.status == MembershipStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already a member of the business.",
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This user already has a membership record. "
                "Use the membership reactivation workflow."
            ),
        )

    agent_role = db.scalar(
        select(Role).where(
            Role.tenant_id == tenant_member.tenant_id,
            Role.code == RoleCode.AGENT_OPERATOR.value,
        )
    )

    if agent_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Business agent role is not configured.",
        )

    membership = TenantMember(
        tenant_id=tenant_member.tenant_id,
        user_id=agent.id,
        role_id=agent_role.id,
        status=MembershipStatus.ACTIVE,
    )

    try:
        db.add(membership)
        db.commit()
        db.refresh(membership)
        return membership

    except Exception:
        db.rollback()
        raise


def list_members(
    db: Session,
    tenant_member: TenantMember,
) -> list[TenantMember]:
    statement = (
        select(TenantMember)
        .where(
            TenantMember.tenant_id == tenant_member.tenant_id,
        )
        .order_by(TenantMember.joined_at.asc())
    )

    return list(db.scalars(statement).all())
