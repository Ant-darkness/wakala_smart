import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.config import settings
from app.core.security import (
    generate_random_token,
    generate_refresh_token,
    hash_password,
    hash_random_token,
    hash_refresh_token,
    verify_password,
)
from app.models.email_verification_token import EmailVerificationToken
from app.models.enums import UserStatus
from app.models.user import User
from app.models.user_session import UserSession
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

REFRESH_TOKEN_EXPIRE_DAYS = 30
EMAIL_VERIFICATION_EXPIRE_MINUTES = 30


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _deliver_verification_email(email: str, token: str) -> None:
    """
    Development adapter.
    Replace with a real email provider before production deployment.
    """
    if settings.APP_ENV == "development":
        logger.warning(
            "Development email verification token for %s: %s",
            email,
            token,
        )
        return

    raise RuntimeError("Email delivery provider is not configured.")


def create_email_verification(
    db: Session,
    user: User,
) -> None:
    raw_token = generate_random_token()

    verification = EmailVerificationToken(
        user_id=user.id,
        token_hash=hash_random_token(raw_token),
        expires_at=_utc_now() + timedelta(minutes=EMAIL_VERIFICATION_EXPIRE_MINUTES),
    )

    db.add(verification)
    db.flush()

    _deliver_verification_email(user.email, raw_token)


def signup(db: Session, data) -> dict:
    email = str(data.email).strip().lower()
    phone = data.phone.strip()

    existing_user = db.scalar(
        select(User).where(
            or_(
                User.email == email,
                User.phone == phone,
            )
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or phone already exists.",
        )

    user = User(
        full_name=data.full_name.strip(),
        email=email,
        phone=phone,
        password_hash=hash_password(data.password),
        status=UserStatus.ACTIVE,
        is_email_verified=False,
    )

    try:
        db.add(user)
        db.flush()

        create_email_verification(db, user)

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or phone already exists.",
        ) from None

    except Exception:
        db.rollback()
        raise

    return {
        "message": ("Account created. Check your email for the verification link."),
        "email": user.email,
    }


def verify_email(db: Session, raw_token: str) -> dict:
    token_hash = hash_random_token(raw_token)

    verification = db.scalar(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.token_hash == token_hash)
        .with_for_update()
    )

    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        )

    now = _utc_now()

    if verification.consumed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has already been used.",
        )

    if verification.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired.",
        )

    user = db.scalar(select(User).where(User.id == verification.user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    user.is_email_verified = True
    verification.consumed_at = now

    db.commit()

    return {"message": "Email verified successfully."}


def _create_user_session(
    db: Session,
    user: User,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[str, str]:
    refresh_token = generate_refresh_token()

    session = UserSession(
        user_id=user.id,
        platform_user_id=None,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=_utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=user_agent,
        ip_address=ip_address,
    )

    db.add(session)
    db.flush()

    from app.core.security import create_access_token

    access_token = create_access_token(
        subject=str(user.id),
        session_id=session.id,
        identity_type="user",
    )

    return access_token, refresh_token


def login(
    db: Session,
    email: str,
    password: str,
    user_agent: str | None,
    ip_address: str | None,
) -> dict:
    normalized_email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is None or not verify_password(
        password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not active.",
        )

    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    access_token, refresh_token = _create_user_session(
        db,
        user,
        user_agent,
        ip_address,
    )

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def refresh_session(db: Session, raw_refresh_token: str) -> dict:
    token_hash = hash_refresh_token(raw_refresh_token)

    session = db.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == token_hash).with_for_update()
    )

    now = _utc_now()

    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= now
        or session.user_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user = db.scalar(select(User).where(User.id == session.user_id))

    if user is None or user.status != UserStatus.ACTIVE or not user.is_email_verified:
        session.revoked_at = now
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not eligible for authentication.",
        )

    new_refresh_token = generate_refresh_token()

    session.refresh_token_hash = hash_refresh_token(new_refresh_token)
    session.expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    from app.core.security import create_access_token

    access_token = create_access_token(
        subject=str(user.id),
        session_id=session.id,
        identity_type="user",
    )

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def logout(db: Session, raw_refresh_token: str) -> dict:
    token_hash = hash_refresh_token(raw_refresh_token)

    session = db.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == token_hash).with_for_update()
    )

    if session is not None and session.revoked_at is None:
        session.revoked_at = _utc_now()
        db.commit()

    return {"message": "Logged out successfully."}


def logout_all_sessions(db: Session, user_id: UUID) -> dict:
    sessions = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        )
    ).all()

    now = _utc_now()

    for session in sessions:
        session.revoked_at = now

    db.commit()

    return {"message": "All sessions have been revoked."}
