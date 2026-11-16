from datetime import UTC
from typing import Annotated
from uuid import UUID

import jwt
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserStatus
from app.models.platform_user import PlatformUser
from app.models.user import User
from app.models.user_session import UserSession
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

bear_scheme = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# def get_token_payload(
#    token: Annotated[str, Depends(oauth2_scheme)],
# ) -> dict:
#    try:
#        return decode_access_token(token)
#    except jwt.InvalidTokenError:
#        raise unauthorized() from None


def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bear_scheme)],
) -> dict:
    if credentials is None:
        raise unauthorized()

    try:
        return decode_access_token(credentials.credentials)

    except jwt.InvalidTokenError:
        raise unauthorized() from None


def get_active_session(
    payload: Annotated[dict, Depends(get_token_payload)],
    db: Annotated[Session, Depends(get_db)],
) -> UserSession:
    try:
        session_id = UUID(payload["sid"])
    except (ValueError, KeyError, TypeError):
        raise unauthorized() from None

    session = db.scalar(select(UserSession).where(
        UserSession.id == session_id))

    if session is None:
        raise unauthorized()

    from datetime import datetime

    now = datetime.now(UTC)

    if session.revoked_at is not None or session.expires_at <= now:
        raise unauthorized()

    identity_type = payload.get("identity_type")

    if identity_type == "user":
        if session.user_id is None or session.platform_user_id is not None:
            raise unauthorized()

        if str(session.user_id) != payload.get("sub"):
            raise unauthorized()

    elif identity_type == "platform_user":
        if session.platform_user_id is None or session.user_id is not None:
            raise unauthorized()

        if str(session.platform_user_id) != payload.get("sub"):
            raise unauthorized()

    else:
        raise unauthorized()

    return session


def get_current_user(
    payload: Annotated[dict, Depends(get_token_payload)],
    session: Annotated[UserSession, Depends(get_active_session)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if payload.get("identity_type") != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A business user account is required.",
        )

    user = db.scalar(select(User).where(User.id == session.user_id))

    if user is None or user.status != UserStatus.ACTIVE:
        raise unauthorized()

    return user


def get_current_platform_user(
    payload: Annotated[dict, Depends(get_token_payload)],
    session: Annotated[UserSession, Depends(get_active_session)],
    db: Annotated[Session, Depends(get_db)],
) -> PlatformUser:
    if payload.get("identity_type") != "platform_user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A platform administrator account is required.",
        )

    admin = db.scalar(select(PlatformUser).where(
        PlatformUser.id == session.platform_user_id))

    if admin is None or not admin.is_active:
        raise unauthorized()

    return admin
