from decimal import Decimal
from uuid import UUID

from app.models.account import Account
from app.models.daily_archive import DailyArchive
from app.models.daily_register import DailyRegister
from app.models.daily_register_balance import DailyRegisterBalance
from app.models.expense import Expense
from app.models.financial_enums import ExpenseStatus
from app.models.transaction import Transaction
from app.models.transaction_enums import TransactionStatus
from app.modules.archives.schemas import (
    DailyArchiveListResponse,
    DailyArchiveResponse,
)
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def create_daily_archive(
    db: Session,
    *,
    tenant_id: UUID,
    register_id: UUID,
) -> DailyArchiveResponse:

    register = db.scalar(
        select(DailyRegister)
        .where(
            DailyRegister.id == register_id,
            DailyRegister.tenant_id == tenant_id,
        )
        .with_for_update()
    )

    if not register:
        raise HTTPException(404, "Daily register not found")

    if register.status != "CLOSED":
        raise HTTPException(
            409,
            "Only closed registers can be archived",
        )

    existing = db.scalar(select(DailyArchive).where(DailyArchive.register_id == register_id))

    if existing:
        raise HTTPException(
            409,
            "This daily register is already archived",
        )

    balances = db.execute(
        select(
            Account.account_type,
            DailyRegisterBalance.closing_balance,
        )
        .join(
            DailyRegisterBalance,
            DailyRegisterBalance.account_id == Account.id,
        )
        .where(
            DailyRegisterBalance.register_id == register_id,
            Account.tenant_id == tenant_id,
        )
    ).all()

    account_snapshot = {str(account_type): str(balance) for account_type, balance in balances}

    transactions = db.execute(
        select(
            Transaction.status,
            func.count(Transaction.id),
            func.coalesce(func.sum(Transaction.amount), 0),
            func.coalesce(func.sum(Transaction.commission), 0),
        )
        .where(
            Transaction.tenant_id == tenant_id,
            Transaction.occurred_at >= register.business_date,
            Transaction.occurred_at
            < (register.business_date + __import__("datetime").timedelta(days=1)),
        )
        .group_by(Transaction.status)
    ).all()

    transaction_summary = {}
    counts = {
        "total": 0,
        "paid": 0,
        "pending": 0,
        "debt": 0,
        "returned": 0,
    }

    total_commission = Decimal("0")
    total_amount = Decimal("0")

    for status, count, amount, commission in transactions:
        key = str(status)
        transaction_summary[key] = {
            "count": count,
            "amount": str(amount),
            "commission": str(commission),
        }

        counts["total"] += count
        total_amount += Decimal(str(amount))

        if key == TransactionStatus.PAYED.value:
            counts["paid"] += count
            total_commission += Decimal(str(commission))
        elif key == TransactionStatus.PENDING.value:
            counts["pending"] += count
        elif key == TransactionStatus.DEBT.value:
            counts["debt"] += count
        elif key == TransactionStatus.RETURNED.value:
            counts["returned"] += count

    expenses = db.execute(
        select(
            Expense.expense_status,
            func.coalesce(func.sum(Expense.amount), 0),
        )
        .where(
            Expense.tenant_id == tenant_id,
            Expense.occurred_at >= register.business_date,
            Expense.occurred_at
            < (register.business_date + __import__("datetime").timedelta(days=1)),
        )
        .group_by(Expense.expense_status)
    ).all()

    expense_summary = {}
    capital_expenses = Decimal("0")
    extra_expenses = Decimal("0")

    for status, amount in expenses:
        expense_summary[str(status)] = str(amount)

        if status == ExpenseStatus.FROM_CAPITAL:
            capital_expenses = Decimal(str(amount))
        elif status == ExpenseStatus.EXTRA:
            extra_expenses = Decimal(str(amount))

    net_profit = total_commission - capital_expenses

    archive = DailyArchive(
        tenant_id=tenant_id,
        register_id=register_id,
        business_date=register.business_date,
        opening_master_capital=register.opening_master_capital,
        closing_master_capital=register.closing_master_capital,
        total_transactions=counts["total"],
        paid_transactions=counts["paid"],
        pending_transactions=counts["pending"],
        debt_transactions=counts["debt"],
        returned_transactions=counts["returned"],
        total_commission=total_commission,
        capital_expenses=capital_expenses,
        extra_expenses=extra_expenses,
        net_profit=net_profit,
        account_balances=account_snapshot,
        transaction_summary=transaction_summary,
        expense_summary=expense_summary,
    )

    try:
        
        db.add(archive)
        db.flush()
        db.refresh(archive)
        
    except Exception:
        db.rollback()
        raise

    return DailyArchiveResponse.model_validate(archive)


def list_daily_archives(
    db: Session,
    *,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> DailyArchiveListResponse:

    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(422, "Invalid pagination")

    query = select(DailyArchive).where(DailyArchive.tenant_id == tenant_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    items = db.scalars(
        query.order_by(DailyArchive.business_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return DailyArchiveListResponse(
        items=[DailyArchiveResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
