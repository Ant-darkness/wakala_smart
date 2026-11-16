import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "recipient_user_id",
            "dedupe_key",
            name="uq_notification_dedupe",
        ),
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_notification_title_nonempty",
        ),
        CheckConstraint(
            "length(trim(body)) > 0",
            name="ck_notification_body_nonempty",
        ),
        CheckConstraint(
            "length(trim(notification_type)) > 0",
            name="ck_notification_type_nonempty",
        ),
        CheckConstraint(
            "dedupe_key IS NULL OR length(trim(dedupe_key)) > 0",
            name="ck_notification_dedupe_key_nonempty",
        ),
        CheckConstraint(
            "(is_read = TRUE AND read_at IS NOT NULL) OR (is_read = FALSE AND read_at IS NULL)",
            name="ck_notification_read_state",
        ),
        Index(
            "ix_notification_recipient_feed",
            "tenant_id",
            "recipient_user_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_notification_unread",
            "tenant_id",
            "recipient_user_id",
            "created_at",
            postgresql_where=text("is_read = false"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    dedupe_key: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
