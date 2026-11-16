
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
    text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.register_enums import DailyRegisterStatus


class DailyRegister(Base):
    __tablename__ = "daily_registers"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "business_date",
            name="uq_daily_registers_tenant_date",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_daily_registers_tenant_id_id",
        ),
        CheckConstraint(
            "opening_master_capital >= 0",
            name="ck_register_opening_capital_nonnegative",
        ),
        CheckConstraint(
            "closing_master_capital IS NULL OR closing_master_capital >= 0",
            name="ck_register_closing_capital_nonnegative",
        ),
        CheckConstraint(
            """
            (status = 'OPEN' AND closed_at IS NULL AND closed_by_user_id IS NULL)
            OR
            (status = 'CLOSED' AND closed_at IS NOT NULL AND closed_by_user_id IS NOT NULL)
            """,
            name="ck_daily_register_status_timestamps",
        ),
        Index(
            "ix_daily_registers_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "uq_daily_registers_one_open_per_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
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

    business_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    status: Mapped[DailyRegisterStatus] = mapped_column(
        Enum(
            DailyRegisterStatus,
            name="daily_register_status",
            native_enum=True,
            values_callable=lambda cls: [item.value for item in cls],
        ),
        nullable=False,
        default=DailyRegisterStatus.OPEN,
        server_default=DailyRegisterStatus.OPEN.value,
    )

    opening_master_capital: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    closing_master_capital: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    opened_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
