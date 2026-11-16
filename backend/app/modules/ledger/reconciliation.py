from decimal import Decimal
from uuid import UUID

from app.models.account import Account
from app.models.ledger import JournalLine, LedgerAccount
from sqlalchemy import func, select
from sqlalchemy.orm import Session

ACCOUNT_LEDGER_CODES = {
    "CASH": "1000",
    "MPESA": "1010",
    "HALOPESA": "1020",
    "AIRTEL_MONEY": "1030",
    "TIGO_YAS": "1040",
}


def reconcile_tenant_accounts(
    db: Session,
    *,
    tenant_id: UUID,
) -> list[dict]:
    accounts = db.scalars(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.is_active.is_(True),
        )
    ).all()

    report = []

    for account in accounts:
        code = ACCOUNT_LEDGER_CODES.get(account.account_type.value)

        if not code:
            continue

        ledger_account = db.scalar(
            select(LedgerAccount).where(
                LedgerAccount.tenant_id == tenant_id,
                LedgerAccount.code == code,
            )
        )

        if not ledger_account:
            report.append(
                {
                    "account_type": code,
                    "account_balance": str(account.balance),
                    "ledger_balance": None,
                    "difference": None,
                    "status": "LEDGER_ACCOUNT_MISSING",
                }
            )
            continue

        debit_total, credit_total = db.execute(
            select(
                func.coalesce(func.sum(JournalLine.debit), 0),
                func.coalesce(func.sum(JournalLine.credit), 0),
            ).where(JournalLine.ledger_account_id == ledger_account.id)
        ).one()

        ledger_balance = Decimal(str(debit_total)) - Decimal(str(credit_total))

        difference = Decimal(str(account.balance)) - ledger_balance

        report.append(
            {
                "account_type": code,
                "account_balance": str(account.balance),
                "ledger_balance": str(ledger_balance),
                "difference": str(difference),
                "status": ("MATCHED" if difference == 0 else "MISMATCH"),
            }
        )

    return report
