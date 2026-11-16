from datetime import UTC, datetime, timedelta

from app.core.security import generate_random_token, hash_random_token
from app.models.enums import MembershipStatus, TenantStatus, UserStatus
from app.models.member_invitation import MemberInvitation
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.tenant_member import TenantMember
from app.models.user import User
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

INVITATION_EXPIRE_HOURS = 48


def _now() -> datetime:
    return datetime.now(UTC)


def create_invitation(
    db: Session,
    tenant_member: TenantMember,
    email: str,
) -> tuple[MemberInvitation, str]:
    normalized_email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered user found with this email.",
        )

    if user.status != UserStatus.ACTIVE or not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not eligible for invitation.",
        )

    if user.id == tenant_member.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot invite yourself.",
        )

    # existing_membership = db.scalar(
    #    select(TenantMember).where(
    #        TenantMember.tenant_id == tenant_member.tenant_id,
    #        TenantMember.user_id == user.id,
    #    )
    # )

    tenant = db.scalar(
        select(TenantMember).where(
            TenantMember.tenant_id == tenant_member.tenant_id,
            TenantMember.user_id == user.id,
        )
    )

    if (
        tenant is None or tenant.deleted_at is not None or tenant.status != TenantStatus.ACTIVE
        # existing_membership is not None
        # and existing_membership.status == MembershipStatus.ACTIVE
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already an active business member.",
        )

    role = db.scalar(
        select(Role).where(
            Role.tenant_id == tenant_member.tenant_id,
            Role.code == "AGENT_OPERATOR",
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent role is not configured.",
        )

    pending = db.scalar(
        select(MemberInvitation).where(
            MemberInvitation.tenant_id == tenant_member.tenant_id,
            MemberInvitation.invited_user_id == user.id,
            MemberInvitation.status == "PENDING",
            MemberInvitation.expires_at > _now(),
            MemberInvitation.revoked_at.is_(None),
        )
    )

    if pending is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active invitation already exists.",
        )

    raw_token = generate_random_token()

    invitation = MemberInvitation(
        tenant_id=tenant_member.tenant_id,
        invited_user_id=user.id,
        invited_by_user_id=tenant_member.user_id,
        role_id=role.id,
        token_hash=hash_random_token(raw_token),
        status="PENDING",
        expires_at=_now() + timedelta(hours=INVITATION_EXPIRE_HOURS),
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return invitation, raw_token


def accept_invitation(
    db: Session,
    current_user: User,
    raw_token: str,
) -> TenantMember:
    token_hash = hash_random_token(raw_token)

    invitation = db.scalar(
        select(MemberInvitation).where(MemberInvitation.token_hash == token_hash).with_for_update()
    )

    now = _now()

    if (
        invitation is None
        or invitation.status != "PENDING"
        or invitation.revoked_at is not None
        or invitation.expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is invalid, expired, or unavailable.",
        )

    if invitation.invited_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation belongs to another user.",
        )

    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before accepting an invitation.",
        )

    tenant = db.scalar(
        select(Tenant).where(
            Tenant.id == invitation.tenant_id,
        )
    )

    if tenant is None or tenant.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business is unavailable.",
        )

    membership = db.scalar(
        select(TenantMember)
        .where(
            TenantMember.tenant_id == invitation.tenant_id,
            TenantMember.user_id == current_user.id,
        )
        .with_for_update()
    )

    if membership is None:
        membership = TenantMember(
            tenant_id=invitation.tenant_id,
            user_id=current_user.id,
            role_id=invitation.role_id,
            status=MembershipStatus.ACTIVE,
        )
        db.add(membership)

    elif membership.status == MembershipStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already an active member.",
        )

    else:
        membership.role_id = invitation.role_id
        membership.status = MembershipStatus.ACTIVE

    invitation.status = "ACCEPTED"
    invitation.accepted_at = now

    db.commit()
    db.refresh(membership)

    return membership


def revoke_invitation(
    db: Session,
    tenant_member: TenantMember,
    invitation_id,
) -> dict:
    invitation = db.scalar(
        select(MemberInvitation)
        .where(
            MemberInvitation.id == invitation_id,
            MemberInvitation.tenant_id == tenant_member.tenant_id,
        )
        .with_for_update()
    )

    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found.",
        )

    if invitation.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending invitations can be revoked.",
        )

    invitation.status = "REVOKED"
    invitation.revoked_at = _now()

    db.commit()

    return {"message": "Invitation revoked successfully."}
