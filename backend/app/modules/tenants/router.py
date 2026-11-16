from typing import Annotated

from app.db.session import get_db
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.tenants import service
from app.modules.tenants.schemas import (
    TenantCreateRequest,
    TenantListResponse,
    TenantResponse,
)
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/tenants", tags=["Tenants"])

DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_business(
    data: TenantCreateRequest,
    user: CurrentUser,
    db: DatabaseSession,
):
    return service.create_tenant(
        db=db,
        owner=user,
        name=data.name,
    )


@router.get("", response_model=TenantListResponse)
def list_my_businesses(
    user: CurrentUser,
    db: DatabaseSession,
):
    tenants = service.get_user_tenants(db, user)

    return {
        "items": tenants,
        "total": len(tenants),
    }
