import uuid

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class DailyArchive(Base, TimestampMixin):
    __tablename__ = "daily_archives"

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

    register_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_registers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    business_date: Mapped[object] = mapped_column(
        Date,
        nullable=False,
    )

    opening_master_capital: Mapped[object] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    closing_master_capital: Mapped[object] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    total_transactions: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    paid_transactions: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    pending_transactions: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    debt_transactions: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    returned_transactions: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    total_commission: Mapped[object] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    capital_expenses: Mapped[object] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    extra_expenses: Mapped[object] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    net_profit: Mapped[object] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    account_balances: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    transaction_summary: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    expense_summary: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    __table_args__ = (
        UniqueConstraint(
            "register_id",
            name="uq_daily_archives_register",
        ),
        CheckConstraint(
            "total_transactions >= 0",
            name="ck_archive_total_transactions",
        ),
        CheckConstraint(
            "paid_transactions >= 0",
            name="ck_archive_paid_transactions",
        ),
        Index(
            "ix_daily_archives_tenant_date",
            "tenant_id",
            "business_date",
        ),
    )
