
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.models.transaction_enums import (
    SyncStatus,
    TransactionNetwork,
    TransactionStatus,
    TransactionType,
)


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    reference: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    commission: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type"),
        nullable=False,
    )

    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status"),
        nullable=False,
        default=TransactionStatus.PENDING,
    )

    network: Mapped[TransactionNetwork] = mapped_column(
        Enum(TransactionNetwork, name="transaction_network"),
        nullable=False,
    )

    raw_sms_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sms_fingerprint: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    grace_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_pending_debt: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_reversed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    balance_applied: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="sync_status"),
        nullable=False,
        default=SyncStatus.SYNCED,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "account_id"],
            ["accounts.tenant_id", "accounts.id"],
            name="fk_transactions_tenant_account",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_transactions_amount_positive",
        ),
        CheckConstraint(
            "fee >= 0 AND commission >= 0",
            name="ck_transactions_fee_commission_non_negative",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_transactions_tenant_id_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "network",
            "reference",
            name="uq_transactions_tenant_network_reference",
        ),
        UniqueConstraint(
            "tenant_id",
            "sms_fingerprint",
            name="uq_transactions_tenant_sms_fingerprint",
        ),
        Index(
            "ix_transactions_tenant_occurred",
            "tenant_id",
            "occurred_at",
        ),
        Index(
            "ix_transactions_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_transactions_grace",
            "status",
            "grace_expires_at",
        ),
    )
