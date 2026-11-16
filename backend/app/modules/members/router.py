from typing import Annotated

from app.db.session import get_db
from app.models.tenant_member import TenantMember
from app.modules.members import service
from app.modules.members.schemas import (
    MemberAddRequest,
    MemberResponse,
)
from app.modules.tenants.dependencies import require_permission
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/members",
    tags=["Business Members"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]

CanReadMembers = Annotated[
    TenantMember,
    Depends(require_permission("members.read")),
]

CanAddMembers = Annotated[
    TenantMember,
    Depends(require_permission("members.create")),
]


@router.get("", response_model=list[MemberResponse])
def get_business_members(
    membership: CanReadMembers,
    db: DatabaseSession,
):
    return service.list_members(db, membership)


@router.post(
    "",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_business_agent(
    data: MemberAddRequest,
    membership: CanAddMembers,
    db: DatabaseSession,
):
    return service.add_agent(
        db=db,
        tenant_member=membership,
        email=str(data.email),
    )
