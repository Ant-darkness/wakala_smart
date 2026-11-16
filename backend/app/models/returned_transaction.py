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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.return_enums import ReturnDirection, ReturnSource


class ReturnedTransaction(Base):
    __tablename__ = "returned_transactions"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_returned_transactions_amount_positive",
        ),
        UniqueConstraint(
            "tenant_id",
            "source_fingerprint",
            name="uq_returned_transactions_fingerprint",
        ),
        Index(
            "ix_returned_transactions_tenant_created",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_returned_transactions_tenant_reference",
            "tenant_id",
            "reference",
        ),
        
        ForeignKeyConstraint(
            ["tenant_id", "transaction_id"],
            ["transactions.tenant_id", "transactions.id"],
            name="fk_returned_transactions_tenant_transaction",
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

    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    reference: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    direction: Mapped[ReturnDirection] = mapped_column(
        Enum(
            ReturnDirection,
            name="return_direction",
            native_enum=True,
            values_callable=lambda cls: [item.value for item in cls],
        ),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source: Mapped[ReturnSource] = mapped_column(
        Enum(
            ReturnSource,
            name="return_source",
            native_enum=True,
            values_callable=lambda cls: [item.value for item in cls],
        ),
        nullable=False,
    )

    source_fingerprint: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
