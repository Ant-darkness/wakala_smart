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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.debtor_enums import DebtorStatus


class Debtor(Base):
    __tablename__ = "debtors"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "transaction_id",
            name="uq_debtors_tenant_transaction",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_debtors_amount_positive",
        ),
        Index(
            "ix_debtors_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_debtors_tenant_promised_at",
            "tenant_id",
            "promised_at",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "transaction_id"],
            ["transactions.tenant_id", "transactions.id"],
            name="fk_debtors_tenant_transaction",
            ondelete="RESTRICT",
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

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    reference: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    debtor_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    debtor_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    promised_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[DebtorStatus] = mapped_column(
        Enum(
            DebtorStatus,
            name="debtor_status",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=DebtorStatus.PENDING,
        server_default=DebtorStatus.PENDING.value,
    )

    reminder_enabled: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
