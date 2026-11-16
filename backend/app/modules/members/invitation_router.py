from typing import Annotated
from uuid import UUID

from app.db.session import get_db
from app.models.tenant_member import TenantMember
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.members.invitation_schemas import (
    InvitationAcceptRequest,
    InvitationCreateRequest,
)
from app.modules.members.invitation_service import (
    accept_invitation,
    create_invitation,
    revoke_invitation,
)
from app.modules.tenants.dependencies import require_permission
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/invitations",
    tags=["Member Invitations"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

CanInvite = Annotated[
    TenantMember,
    Depends(require_permission("members.create")),
]

CanManageMembers = Annotated[
    TenantMember,
    Depends(require_permission("members.update")),
]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def invite_agent(
    data: InvitationCreateRequest,
    membership: CanInvite,
    db: DatabaseSession,
):
    invitation, _raw_token = create_invitation(
        db,
        membership,
        str(data.email),
    )

    # Email delivery is intentionally not exposed through this API.
    # Connect a transactional email outbox before production use.
    return {
        "message": "Invitation created.",
        "invitation_id": str(invitation.id),
        "status": invitation.status,
        "expires_at": invitation.expires_at,
        "delivery_status": "PENDING_EMAIL_INTEGRATION",
    }


@router.post("/accept")
def accept_agent_invitation(
    data: InvitationAcceptRequest,
    user: CurrentUser,
    db: DatabaseSession,
):
    membership = accept_invitation(
        db,
        user,
        data.token,
    )

    return {
        "message": "Invitation accepted.",
        "membership_id": str(membership.id),
        "tenant_id": str(membership.tenant_id),
        "status": membership.status,
    }


@router.post("/{invitation_id}/revoke")
def revoke_agent_invitation(
    invitation_id: UUID,
    membership: CanManageMembers,
    db: DatabaseSession,
):
    return revoke_invitation(
        db,
        membership,
        invitation_id,
    )
