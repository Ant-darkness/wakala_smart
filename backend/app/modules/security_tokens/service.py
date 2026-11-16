from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.security import (
    generate_security_token,
    hash_security_token,
    verify_password,
    verify_security_token,
)
from app.models.security_event import SecurityEvent
from app.models.user import User
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

LOCKOUT_MINUTES = [15, 30, 60, 240, 1440]
MAX_FAILED_ATTEMPTS = 5


def _record_security_event(
    db: Session,
    *,
    user_id: UUID,
    event_type: str,
    severity: str = "LOW",
    details: dict | None = None,
) -> None:
    db.add(
        SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            details=details,
        )
    )


def verify_user_security_token(
    db: Session,
    *,
    user_id: UUID,
    token: str,
) -> bool:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    now = datetime.now(UTC)

    if user.security_token_locked_until:
        locked_until = user.security_token_locked_until

        if locked_until > now:
            remaining = int((locked_until - now).total_seconds())

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Security Token verification is temporarily locked.",
                    "retry_after_seconds": remaining,
                },
            )

        user.security_token_locked_until = None
        user.security_token_failed_attempts = 0

    if not user.security_token_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Token has not been configured.",
        )

    if not verify_security_token(token, user.security_token_hash):
        user.security_token_failed_attempts += 1

        if user.security_token_failed_attempts >= MAX_FAILED_ATTEMPTS:
            level = min(
                user.security_token_lockout_level,
                len(LOCKOUT_MINUTES) - 1,
            )

            lockout_duration = LOCKOUT_MINUTES[level]

            user.security_token_lockout_level = min(
                user.security_token_lockout_level + 1,
                len(LOCKOUT_MINUTES),
            )

            user.security_token_locked_until = now + timedelta(minutes=lockout_duration)

            user.security_token_failed_attempts = 0

            _record_security_event(
                db,
                user_id=user.id,
                event_type="SECURITY_TOKEN_LOCKED",
                severity="HIGH",
                details={
                    "lockout_minutes": lockout_duration,
                },
            )
        else:
            _record_security_event(
                db,
                user_id=user.id,
                event_type="SECURITY_TOKEN_VERIFICATION_FAILED",
                severity="MEDIUM",
                details={
                    "failed_attempts": user.security_token_failed_attempts,
                },
            )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Security Token.",
        )

    user.security_token_failed_attempts = 0

    _record_security_event(
        db,
        user_id=user.id,
        event_type="SECURITY_TOKEN_VERIFIED",
        severity="LOW",
    )

    db.commit()

    return True


def reset_user_security_token(
    db: Session,
    *,
    user_id: UUID,
    current_password: str,
) -> str:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user.password_hash or not verify_password(
        current_password,
        user.password_hash,
    ):
        _record_security_event(
            db,
            user_id=user.id,
            event_type="SECURITY_TOKEN_RESET_FAILED",
            severity="HIGH",
        )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Primary authentication verification failed.",
        )

    new_token = generate_security_token()

    user.security_token_hash = hash_security_token(new_token)
    user.security_token_failed_attempts = 0
    user.security_token_lockout_level = 0
    user.security_token_locked_until = None

    _record_security_event(
        db,
        user_id=user.id,
        event_type="SECURITY_TOKEN_RESET",
        severity="HIGH",
    )

    db.commit()
    db.refresh(user)

    return new_token
