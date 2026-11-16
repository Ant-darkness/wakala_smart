from decimal import Decimal
from uuid import UUID

from app.models.ledger import JournalEntry
from app.modules.ledger.helpers import get_ledger_account
from app.modules.ledger.service import post_journal_entry
from fastapi import HTTPException
from sqlalchemy.orm import Session


def post_commission_income(
    db: Session,
    *,
    tenant_id: UUID,
    transaction_id: UUID,
    commission: Decimal,
    user_id: UUID | None,
) -> JournalEntry | None:
    amount = Decimal(str(commission))
    if not amount.is_finite():
        raise HTTPException(
            422,
            "Amount must be a finite number",
        )

    if amount < 0:
        raise HTTPException(
            422,
            "Commission cannot be negative",
        )

    if amount == 0:
        return None

    receivable = get_ledger_account(
        db,
        tenant_id=tenant_id,
        code="1100",
    )

    commission_income = get_ledger_account(
        db,
        tenant_id=tenant_id,
        code="4000",
    )

    return post_journal_entry(
        db,
        tenant_id=tenant_id,
        source_type="TRANSACTION_COMMISSION",
        source_id=str(transaction_id),
        description="Recognized transaction commission",
        created_by_user_id=user_id,
        lines=[
            {
                "ledger_account_id": receivable.id,
                "debit": amount,
                "credit": Decimal("0"),
            },
            {
                "ledger_account_id": commission_income.id,
                "debit": Decimal("0"),
                "credit": amount,
            },
        ],
    )


def post_capital_expense(
    db: Session,
    *,
    tenant_id: UUID,
    expense_id: UUID,
    payment_ledger_code: str,
    amount: Decimal,
    user_id: UUID | None,
) -> JournalEntry | None:
    value = Decimal(str(amount))
    if not value.is_finite():
        raise HTTPException(
            422,
            "Amount must be a finite number",
        )

    if value <= 0:
        raise HTTPException(
            422,
            "Expense amount must be greater than zero",
        )

    expense_account = get_ledger_account(
        db,
        tenant_id=tenant_id,
        code="5000",
    )

    payment_account = get_ledger_account(
        db,
        tenant_id=tenant_id,
        code=payment_ledger_code,
    )

    return post_journal_entry(
        db,
        tenant_id=tenant_id,
        source_type="CAPITAL_EXPENSE",
        source_id=str(expense_id),
        description="Capital-funded business expense",
        created_by_user_id=user_id,
        lines=[
            {
                "ledger_account_id": expense_account.id,
                "debit": value,
                "credit": Decimal("0"),
            },
            {
                "ledger_account_id": payment_account.id,
                "debit": Decimal("0"),
                "credit": value,
            },
        ],
    )


def post_float_shift(
    db: Session,
    *,
    tenant_id: UUID,
    adjustment_id: UUID,
    source_ledger_code: str,
    destination_ledger_code: str,
    amount: Decimal,
    user_id: UUID | None,
) -> JournalEntry:
    value = Decimal(str(amount))
    if not value.is_finite():
        raise HTTPException(
            422,
            "Amount must be a finite number",
        )

    if value <= 0:
        raise HTTPException(
            422,
            "Float shift amount must be positive",
        )

    source = get_ledger_account(
        db,
        tenant_id=tenant_id,
        code=source_ledger_code,
    )

    destination = get_ledger_account(
        db,
        tenant_id=tenant_id,
        code=destination_ledger_code,
    )

    if source.id == destination.id:
        raise HTTPException(
            422,
            "Source and destination must be different",
        )

    return post_journal_entry(
        db,
        tenant_id=tenant_id,
        source_type="FLOAT_SHIFT",
        source_id=str(adjustment_id),
        description="Float transfer between network accounts",
        created_by_user_id=user_id,
        lines=[
            {
                "ledger_account_id": destination.id,
                "debit": value,
                "credit": Decimal("0"),
            },
            {
                "ledger_account_id": source.id,
                "debit": Decimal("0"),
                "credit": value,
            },
        ],
    )
