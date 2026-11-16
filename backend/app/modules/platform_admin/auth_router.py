from typing import Annotated

from app.db.session import get_db
from app.models.platform_user import PlatformUser
from app.modules.auth.dependencies import get_current_platform_user
from app.modules.platform_admin.auth_schemas import (
    PlatformAdminResponse,
    PlatformLoginRequest,
    PlatformTokenResponse,
)
from app.modules.platform_admin.auth_service import platform_login
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/platform/auth",
    tags=["Platform Authentication"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]

CurrentPlatformAdmin = Annotated[
    PlatformUser,
    Depends(get_current_platform_user),
]


@router.post(
    "/login",
    response_model=PlatformTokenResponse,
)
def login(
    data: PlatformLoginRequest,
    request: Request,
    db: DatabaseSession,
):
    return platform_login(
        db=db,
        email=str(data.email),
        password=data.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=(request.client.host if request.client else None),
    )


@router.get(
    "/me",
    response_model=PlatformAdminResponse,
)
def get_me(admin: CurrentPlatformAdmin):
    return admin
