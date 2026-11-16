
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.financial_enums import CapitalAdjustmentType


class CapitalAdjustment(Base):
    __tablename__ = "capital_adjustments"

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "source_account_id"],
            ["accounts.tenant_id", "accounts.id"],
            name="fk_capital_adjustment_tenant_source_account",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "destination_account_id"],
            ["accounts.tenant_id", "accounts.id"],
            name="fk_capital_adjustment_tenant_destination_account",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "reference",
            name="uq_capital_adjustment_tenant_reference",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_capital_adjustment_amount_positive",
        ),
        CheckConstraint(
            "master_capital_before >= 0 AND master_capital_after >= 0",
            name="ck_capital_adjustment_capital_nonnegative",
        ),
        CheckConstraint(
            "source_account_id IS NULL OR source_account_id <> destination_account_id",
            name="ck_capital_adjustment_distinct_accounts",
        ),
        Index(
            "ix_capital_adjustments_tenant_created",
            "tenant_id",
            "created_at",
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

    source_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    destination_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    adjustment_type: Mapped[CapitalAdjustmentType] = mapped_column(
        Enum(
            CapitalAdjustmentType,
            name="capital_adjustment_type",
            native_enum=True,
            values_callable=lambda cls: [item.value for item in cls],
        ),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    master_capital_before: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    master_capital_after: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    reference: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
