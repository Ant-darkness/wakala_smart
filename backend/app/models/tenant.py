
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import TenantStatus
from app.models.mixins import TimestampMixin


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_tenants_name_nonempty",
        ),
        CheckConstraint(
            "length(trim(slug)) > 0",
            name="ck_tenants_slug_nonempty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    status: Mapped[TenantStatus] = mapped_column(
        SAEnum(
            TenantStatus,
            name="tenant_status",
            values_callable=lambda cls: [item.value for item in cls],
        ),
        nullable=False,
        default=TenantStatus.ACTIVE,
        server_default=TenantStatus.ACTIVE.value,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
