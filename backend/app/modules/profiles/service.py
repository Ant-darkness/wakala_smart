import secrets
from uuid import UUID

from app.core.security import (
    generate_security_token,
    hash_security_token,
)
from app.models.user import User
from app.modules.audit.service import record_user_action
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _generate_agent_number() -> str:
    """
    Generate an agent number.
    The database unique constraint remains the final
    protection against duplicate numbers.
    """
    return f"WS{secrets.randbelow(100_000_000):08d}"


def setup_profile(
    db: Session,
    *,
    user_id: UUID,
    full_name: str,
    phone: str,
    tin: str | None = None,
    nida: str | None = None,
    profile_image_url: str | None = None,
) -> tuple[User, str]:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before completing your profile.",
        )

    if user.agent_number is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile setup has already been completed.",
        )

    normalized_phone = phone.strip()

    phone_owner = db.scalar(
        select(User).where(
            User.phone == normalized_phone,
            User.id != user_id,
        )
    )

    if phone_owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This phone number is already registered.",
        )

    agent_number = None

    for _ in range(5):
        candidate = _generate_agent_number()

        existing = db.scalar(select(User.id).where(User.agent_number == candidate))

        if existing is None:
            agent_number = candidate
            break

    if agent_number is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not allocate an agent number. Please retry.",
        )

    security_token = generate_security_token()

    user.full_name = full_name.strip()
    user.phone = normalized_phone
    user.tin = tin.strip() if tin else None
    user.nida = nida.strip() if nida else None
    user.profile_image_url = profile_image_url
    user.agent_number = agent_number
    user.security_token_hash = hash_security_token(security_token)

    record_user_action(
        db,
        user_id=user.id,
        action="PROFILE_SETUP_COMPLETED",
        resource_type="USER_PROFILE",
        resource_id=user.id,
        after_data={
            "agent_number": agent_number,
            "profile_completed": True,
        },
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A unique profile value conflicts with another user.",
        )

    db.refresh(user)

    return user, security_token


def update_profile(
    db: Session,
    *,
    user_id: UUID,
    # security_token: str,
    updates: dict,
) -> User:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user.security_token_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Token setup is required.",
        )

    # if not verify_security_token(
    #    security_token,
    #    user.security_token_hash,
    # ):
    #    raise HTTPException(
    #        status_code=status.HTTP_403_FORBIDDEN,
    #        detail="Invalid Security Token.",
    #    )

    if "agent_number" in updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent number cannot be changed through profile updates.",
        )

    if "email" in updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email changes must use the dedicated email verification flow.",
        )

    phone = updates.get("phone")

    if phone:
        normalized_phone = phone.strip()

        phone_owner = db.scalar(
            select(User).where(
                User.phone == normalized_phone,
                User.id != user_id,
            )
        )

        if phone_owner:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This phone number is already registered.",
            )

        updates["phone"] = normalized_phone

    allowed_fields = {
        "full_name",
        "phone",
        "tin",
        "nida",
        "profile_image_url",
    }

    invalid_fields = set(updates) - allowed_fields

    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported profile fields: {sorted(invalid_fields)}",
        )

    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip() or None

        setattr(user, field, value)

    record_user_action(
        db,
        user_id=user.id,
        action="PROFILE_UPDATED",
        resource_type="USER_PROFILE",
        resource_id=user.id,
        after_data={
            "updated_fields": sorted(updates.keys()),
        },
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A unique profile value conflicts with another user.",
        )

    db.refresh(user)
    return user
