from uuid import UUID

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.notifications.schemas import (
    NotificationFeedResponse,
    NotificationReadAllResponse,
    NotificationReadResponse,
)
from app.modules.notifications.service import (
    get_notification_feed,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)
from app.modules.tenants.dependencies import get_current_tenant_member
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "/feed",
    response_model=NotificationFeedResponse,
)
def notification_feed(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    current_user=Depends(get_current_user),
):
    return get_notification_feed(
        db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationReadResponse,
)
def read_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    current_user=Depends(get_current_user),
):
    notification = mark_notification_as_read(
        db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        notification_id=notification_id,
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    return notification


@router.post(
    "/read-all",
    response_model=NotificationReadAllResponse,
)
def read_all_notifications(
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    current_user=Depends(get_current_user),
):
    count = mark_all_notifications_as_read(
        db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
    )

    return {"updated_count": count}
