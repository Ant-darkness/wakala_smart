from uuid import UUID

from app.models.platform_user import PlatformUser
from app.modules.audit.service import record_platform_action
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def update_platform_admin_status(
    db: Session,
    *,
    current_admin_id: UUID,
    target_admin_id: UUID,
    is_active: bool,
    reason: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    if current_admin_id == target_admin_id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    target = db.scalar(
        select(PlatformUser).where(PlatformUser.id == target_admin_id).with_for_update()
    )

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform administrator not found.",
        )

    if target.is_active == is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account already has the requested status.",
        )

    if not is_active:
        active_count = (
            db.scalar(select(func.count(PlatformUser.id)).where(PlatformUser.is_active.is_(True)))
            or 0
        )

        if active_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The last active platform administrator cannot be deactivated.",
            )

    previous_status = target.is_active
    target.is_active = is_active

    record_platform_action(
        db,
        admin_id=current_admin_id,
        action=("PLATFORM_ADMIN_ACTIVATED" if is_active else "PLATFORM_ADMIN_DEACTIVATED"),
        resource_type="PLATFORM_ADMIN",
        resource_id=target.id,
        before_data={"is_active": previous_status},
        after_data={"is_active": is_active},
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Platform administrator status updated.",
        "admin_id": str(target.id),
        "previous_status": previous_status,
        "current_status": target.is_active,
    }
