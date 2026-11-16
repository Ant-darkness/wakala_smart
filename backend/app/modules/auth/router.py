from typing import Annotated

from app.db.session import get_db
from app.modules.auth import service
from app.modules.auth.schemas import (
    EmailVerifyRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    SignupRequest,
    TokenResponse,
)
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["Authentication"])

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
)
def signup(
    data: SignupRequest,
    db: DatabaseSession,
):
    return service.signup(db, data)


@router.post("/verify")
def verify_email(
    data: EmailVerifyRequest,
    db: DatabaseSession,
):
    return service.verify_email(db, data.token)


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    request: Request,
    db: DatabaseSession,
):
    return service.login(
        db=db,
        email=str(data.email),
        password=data.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=(request.client.host if request.client else None),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    data: RefreshTokenRequest,
    db: DatabaseSession,
):
    return service.refresh_session(
        db,
        data.refresh_token,
    )


@router.post("/logout")
def logout(
    data: LogoutRequest,
    db: DatabaseSession,
):
    return service.logout(
        db,
        data.refresh_token,
    )
