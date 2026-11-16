
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class DailyArchive(TimestampMixin, Base):
    __tablename__ = "daily_archives"

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "register_id"],
            ["daily_registers.tenant_id", "daily_registers.id"],
            name="fk_daily_archive_tenant_register",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "register_id",
            name="uq_daily_archives_tenant_register",
        ),
        CheckConstraint(
            "opening_master_capital >= 0",
            name="ck_archive_opening_capital_nonnegative",
        ),
        CheckConstraint(
            "closing_master_capital >= 0",
            name="ck_archive_closing_capital_nonnegative",
        ),
        CheckConstraint(
            """
            total_transactions >= 0
            AND paid_transactions >= 0
            AND pending_transactions >= 0
            AND debt_transactions >= 0
            AND returned_transactions >= 0
            """,
            name="ck_archive_transaction_counts_nonnegative",
        ),
        CheckConstraint(
            """
            total_commission >= 0
            AND capital_expenses >= 0
            AND extra_expenses >= 0
            """,
            name="ck_archive_financial_totals_nonnegative",
        ),
        Index(
            "ix_daily_archives_tenant_date",
            "tenant_id",
            "business_date",
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

    register_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    business_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    opening_master_capital: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    closing_master_capital: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    total_transactions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    paid_transactions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    pending_transactions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    debt_transactions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    returned_transactions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    total_commission: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    capital_expenses: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    extra_expenses: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    net_profit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
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
