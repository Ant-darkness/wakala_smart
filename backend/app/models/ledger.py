
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
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

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

    code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    account_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    normal_side: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        default="DEBIT",
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_ledger_account_tenant_code",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_ledger_account_tenant_id_id",
        ),
        CheckConstraint(
            "account_type IN ('ASSET','LIABILITY','EQUITY','INCOME','EXPENSE')",
            name="ck_ledger_account_type",
        ),
        CheckConstraint(
            "normal_side IN ('DEBIT','CREDIT')",
            name="ck_ledger_normal_side",
        ),
        CheckConstraint(
            "length(trim(code)) > 0",
            name="ck_ledger_account_code_nonempty",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_ledger_account_name_nonempty",
        ),
        Index(
            "ix_ledger_accounts_tenant",
            "tenant_id",
        ),
    )


class JournalEntry(Base):
    __tablename__ = "journal_entries"

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

    source_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    source_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_type",
            "source_id",
            name="uq_journal_source",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_journal_entry_tenant_id_id",
        ),
        CheckConstraint(
            "length(trim(source_type)) > 0",
            name="ck_journal_source_type_nonempty",
        ),
        CheckConstraint(
            "length(trim(source_id)) > 0",
            name="ck_journal_source_id_nonempty",
        ),
        CheckConstraint(
            "length(trim(description)) > 0",
            name="ck_journal_description_nonempty",
        ),
        Index(
            "ix_journal_entries_tenant_posted",
            "tenant_id",
            "posted_at",
        ),
    )


class JournalLine(Base):
    __tablename__ = "journal_lines"

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

    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    ledger_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    debit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    memo: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "journal_entry_id"],
            ["journal_entries.tenant_id", "journal_entries.id"],
            name="fk_journal_line_tenant_entry",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "ledger_account_id"],
            ["ledger_accounts.tenant_id", "ledger_accounts.id"],
            name="fk_journal_line_tenant_account",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "debit >= 0 AND credit >= 0",
            name="ck_journal_line_nonnegative",
        ),
        CheckConstraint(
            "(debit > 0 AND credit = 0) OR "
            "(credit > 0 AND debit = 0)",
            name="ck_journal_line_one_side",
        ),
        Index(
            "ix_journal_lines_tenant_entry",
            "tenant_id",
            "journal_entry_id",
        ),
        Index(
            "ix_journal_lines_tenant_account",
            "tenant_id",
            "ledger_account_id",
        ),
    )
