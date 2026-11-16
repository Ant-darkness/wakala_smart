from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.models.notification import Notification
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session


def create_notification(
    db: Session,
    *,
    tenant_id: UUID,
    recipient_user_id: UUID,
    notification_type: str,
    title: str,
    body: str,
    payload: dict[str, Any] | None = None,
    dedupe_key: str | None = None,
) -> Notification:
    """
    Create a notification inside the caller's transaction.

    This function deliberately does not commit.
    """

    notification_type = notification_type.strip()
    title = title.strip()
    body = body.strip()

    if not notification_type:
        raise ValueError("Notification type cannot be empty.")

    if len(notification_type) > 80:
        raise ValueError("Notification type cannot exceed 80 characters.")

    if not title or len(title) > 180:
        raise ValueError("Notification title must contain 1-180 characters.")

    if not body:
        raise ValueError("Notification body cannot be empty.")

    if dedupe_key is not None:
        dedupe_key = dedupe_key.strip()

        if not dedupe_key or len(dedupe_key) > 180:
            raise ValueError("Invalid notification deduplication key.")

    if dedupe_key is None:
        notification = Notification(
            tenant_id=tenant_id,
            recipient_user_id=recipient_user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            payload=payload,
        )
        db.add(notification)
        db.flush()
        return notification

    statement = (
        pg_insert(Notification)
        .values(
            tenant_id=tenant_id,
            recipient_user_id=recipient_user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            payload=payload,
            dedupe_key=dedupe_key,
        )
        .on_conflict_do_nothing(constraint="uq_notification_dedupe")
        .returning(Notification.id)
    )

    notification_id = db.execute(statement).scalar_one_or_none()

    if notification_id is None:
        existing = db.scalar(
            select(Notification).where(
                Notification.tenant_id == tenant_id,
                Notification.recipient_user_id == recipient_user_id,
                Notification.dedupe_key == dedupe_key,
            )
        )

        if existing is None:
            raise RuntimeError("Notification deduplication failed unexpectedly.")

        return existing

    notification = db.get(Notification, notification_id)

    if notification is None:
        raise RuntimeError("Created notification could not be loaded.")

    return notification


def get_notification_feed(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    if page < 1:
        raise ValueError("Page must be at least 1.")

    if not 1 <= page_size <= 100:
        raise ValueError("Page size must be between 1 and 100.")

    base_query = select(Notification).where(
        Notification.tenant_id == tenant_id,
        Notification.recipient_user_id == user_id,
    )

    total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0

    unread_count = (
        db.scalar(
            select(func.count()).where(
                Notification.tenant_id == tenant_id,
                Notification.recipient_user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )

    items = db.scalars(
        base_query.order_by(
            Notification.created_at.desc(),
            Notification.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": list(items),
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size,
    }


def mark_notification_as_read(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    notification_id: UUID,
) -> Notification | None:
    try:
        notification = db.scalar(
            select(Notification)
            .where(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,
                Notification.recipient_user_id == user_id,
            )
            .with_for_update()
        )

        if notification is None:
            return None

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(UTC)

            db.commit()
            db.refresh(notification)

        return notification

    except Exception:
        db.rollback()
        raise


def mark_all_notifications_as_read(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
) -> int:
    now = datetime.now(UTC)

    try:
        result = db.execute(
            update(Notification)
            .where(
                Notification.tenant_id == tenant_id,
                Notification.recipient_user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(
                is_read=True,
                read_at=now,
            )
        )

        updated_count = result.rowcount or 0
        db.commit()

        return updated_count

    except Exception:
        db.rollback()
        raise
