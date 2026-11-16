from uuid import UUID

from app.models.ledger import LedgerAccount
from sqlalchemy import select
from sqlalchemy.orm import Session

DEFAULT_ACCOUNTS = [
    ("1000", "Cash", "ASSET", "DEBIT"),
    ("1010", "M-Pesa Float", "ASSET", "DEBIT"),
    ("1020", "HaloPesa Float", "ASSET", "DEBIT"),
    ("1030", "Airtel Money Float", "ASSET", "DEBIT"),
    ("1040", "Tigo/Yas Float", "ASSET", "DEBIT"),
    ("1100", "MNO Receivable", "ASSET", "DEBIT"),
    ("3000", "Owner Capital", "EQUITY", "CREDIT"),
    ("4000", "Commission Income", "INCOME", "CREDIT"),
    ("5000", "Operating Expenses", "EXPENSE", "DEBIT"),
]


def seed_ledger_accounts(
    db: Session,
    *,
    tenant_id: UUID,
) -> None:
    for code, name, account_type, normal_side in DEFAULT_ACCOUNTS:
        existing = db.scalar(
            select(LedgerAccount).where(
                LedgerAccount.tenant_id == tenant_id,
                LedgerAccount.code == code,
            )
        )

        if existing:
            continue

        db.add(
            LedgerAccount(
                tenant_id=tenant_id,
                code=code,
                name=name,
                account_type=account_type,
                normal_side=normal_side,
            )
        )

    db.flush()
