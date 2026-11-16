import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.sms_enums import SmsMessageStatus
from app.models.transaction_enums import TransactionNetwork


class SmsMessage(Base):
    __tablename__ = "sms_messages"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "fingerprint",
            name="uq_sms_message_tenant_fingerprint",
        ),
        Index(
            "ix_sms_message_tenant_status_received",
            "tenant_id",
            "status",
            "received_at",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "transaction_id"],
            ["transactions.tenant_id", "transactions.id"],
            name="fk_sms_messages_tenant_transaction",
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
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    network: Mapped[TransactionNetwork] = mapped_column(
        SAEnum(
            TransactionNetwork,
            name="transaction_network",
            create_type=False,
        ),
        nullable=False,
    )

    raw_body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[SmsMessageStatus] = mapped_column(
        SAEnum(
            SmsMessageStatus,
            name="sms_message_status",
        ),
        nullable=False,
        default=SmsMessageStatus.RECEIVED,
    )

    parsed_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    matched_pattern_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sms_regex_patterns.id", ondelete="SET NULL"),
        nullable=True,
    )

    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
