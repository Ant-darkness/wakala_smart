
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyRegisterBalance(Base):
    __tablename__ = "daily_register_balances"

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "register_id"],
            ["daily_registers.tenant_id", "daily_registers.id"],
            name="fk_register_balance_tenant_register",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "account_id"],
            ["accounts.tenant_id", "accounts.id"],
            name="fk_register_balance_tenant_account",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "register_id",
            "account_id",
            name="uq_daily_register_balance_account",
        ),
        CheckConstraint(
            "opening_balance >= 0",
            name="ck_register_balance_opening_nonnegative",
        ),
        CheckConstraint(
            "closing_balance IS NULL OR closing_balance >= 0",
            name="ck_register_balance_closing_nonnegative",
        ),
        CheckConstraint(
            "(closed_at IS NULL AND closing_balance IS NULL) "
            "OR (closed_at IS NOT NULL AND closing_balance IS NOT NULL)",
            name="ck_register_balance_closing_state",
        ),
        Index(
            "ix_daily_register_balances_register",
            "tenant_id",
            "register_id",
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

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    closing_balance: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
