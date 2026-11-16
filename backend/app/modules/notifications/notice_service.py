from datetime import UTC, datetime
from uuid import UUID

from app.models.notice import Notice
from app.modules.audit.service import (
    record_platform_action,
    record_user_action,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import Session


def _validate_notice(
    *,
    title: str,
    body: str,
    starts_at: datetime,
    ends_at: datetime | None,
) -> tuple[str, str]:
    title = title.strip()
    body = body.strip()

    if not 3 <= len(title) <= 180:
        raise ValueError("Notice title must contain 3-180 characters.")

    if not 1 <= len(body) <= 10_000:
        raise ValueError("Notice body must contain 1-10000 characters.")

    if starts_at.tzinfo is None or starts_at.utcoffset() is None:
        raise ValueError("starts_at must include a timezone.")

    if ends_at is not None:
        if ends_at.tzinfo is None or ends_at.utcoffset() is None:
            raise ValueError("ends_at must include a timezone.")

        if ends_at <= starts_at:
            raise ValueError("ends_at must be after starts_at.")

    return title, body


def create_tenant_notice(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    title: str,
    body: str,
    starts_at: datetime,
    ends_at: datetime | None,
    is_published: bool,
) -> Notice:
    title, body = _validate_notice(
        title=title,
        body=body,
        starts_at=starts_at,
        ends_at=ends_at,
    )

    try:
        notice = Notice(
            tenant_id=tenant_id,
            created_by_user_id=user_id,
            title=title,
            body=body,
            starts_at=starts_at,
            ends_at=ends_at,
            is_published=is_published,
        )

        db.add(notice)
        db.flush()

        record_user_action(
            db,
            user_id=user_id,
            tenant_id=tenant_id,
            action="TENANT_NOTICE_CREATED",
            resource_type="NOTICE",
            resource_id=str(notice.id),
            after_data={
                "title": title,
                "is_published": is_published,
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat() if ends_at else None,
            },
        )

        db.commit()
        db.refresh(notice)

        return notice

    except Exception:
        db.rollback()
        raise


def create_platform_notice(
    db: Session,
    *,
    admin_id: UUID,
    title: str,
    body: str,
    starts_at: datetime,
    ends_at: datetime | None,
    is_published: bool,
) -> Notice:
    title, body = _validate_notice(
        title=title,
        body=body,
        starts_at=starts_at,
        ends_at=ends_at,
    )

    try:
        notice = Notice(
            tenant_id=None,
            created_by_platform_user_id=admin_id,
            title=title,
            body=body,
            starts_at=starts_at,
            ends_at=ends_at,
            is_published=is_published,
        )

        db.add(notice)
        db.flush()

        record_platform_action(
            db,
            admin_id=admin_id,
            action="PLATFORM_NOTICE_CREATED",
            resource_type="NOTICE",
            resource_id=str(notice.id),
            after_data={
                "title": title,
                "is_published": is_published,
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat() if ends_at else None,
            },
        )

        db.commit()
        db.refresh(notice)

        return notice

    except Exception:
        db.rollback()
        raise


def list_visible_notices(
    db: Session,
    *,
    tenant_id: UUID,
) -> list[Notice]:
    now = datetime.now(UTC)

    return list(
        db.scalars(
            select(Notice)
            .where(
                Notice.is_published.is_(True),
                or_(
                    Notice.tenant_id == tenant_id,
                    Notice.tenant_id.is_(None),
                ),
                Notice.starts_at <= now,
                or_(
                    Notice.ends_at.is_(None),
                    Notice.ends_at > now,
                ),
            )
            .order_by(
                Notice.starts_at.desc(),
                Notice.id.desc(),
            )
        ).all()
    )
