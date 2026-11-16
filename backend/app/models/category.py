import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"
    # name = "uq_categories_tenant_name",

    ##__table_args__ = (
    ##    Index(
    ##        "tenant_id",
    ##        func.lower(name),
    ##        unique=True,
    ##    ),
    ##    Index(
    ##        "ix_categories_tenant_active",
    ##        "tenant_id",
    ##        "is_active",
    ##    ),
    ##)

    __table_args__ = (
        Index(
            "uq_categories_tenant_name_lower",
            "tenant_id",
            text("lower(name)"),
            unique=True,
        ),
        Index(
            "ix_categories_tenant_active",
            "tenant_id",
            "is_active",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
