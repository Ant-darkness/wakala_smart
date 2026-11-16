from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.models.platform_user import PlatformUser
from app.models.user_session import UserSession
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

REFRESH_TOKEN_EXPIRE_DAYS = 30


def platform_login(
    db: Session,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> dict:
    normalized_email = email.strip().lower()

    admin = db.scalar(select(PlatformUser).where(PlatformUser.email == normalized_email))

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if admin is None:
        raise invalid_credentials

    if not verify_password(password, admin.password_hash):
        raise invalid_credentials

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform account is disabled.",
        )

    if admin.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="MFA verification flow has not been implemented yet.",
        )

    now = datetime.now(UTC)
    raw_refresh_token = generate_refresh_token()

    session = UserSession(
        platform_user_id=admin.id,
        user_id=None,
        refresh_token_hash=hash_refresh_token(raw_refresh_token),
        expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=user_agent,
        ip_address=ip_address,
    )

    db.add(session)
    db.flush()

    access_token = create_access_token(
        subject=str(admin.id),
        session_id=str(session.id),
        identity_type="platform_user",
    )

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
