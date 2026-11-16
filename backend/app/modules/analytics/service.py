from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from app.models.account import Account
from app.models.debtor import Debtor
from app.models.debtor_enums import DebtorStatus
from app.models.expense import Expense
from app.models.financial_enums import ExpenseStatus
from app.models.tenant_member import TenantMember
from app.models.transaction import Transaction
from app.models.transaction_enums import (
    TransactionStatus,
)
from app.models.user import User
from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

ZERO = Decimal("0.00")


def _utc_range(start_date, end_date):
    if start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date cannot be after end_date",
        )

    start_at = datetime.combine(
        start_date,
        time.min,
        tzinfo=UTC,
    )

    end_at = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
        tzinfo=UTC,
    )

    return start_at, end_at


def _decimal(value) -> Decimal:
    return value if value is not None else ZERO


def get_financial_summary(
    db: Session,
    tenant_id: UUID,
    start_date,
    end_date,
) -> dict:
    start_at, end_at = _utc_range(start_date, end_date)

    transaction_totals = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            Transaction.status == TransactionStatus.PAYED,
                            Transaction.commission,
                        ),
                        else_=ZERO,
                    )
                ),
                ZERO,
            ).label("commission"),
            func.count(Transaction.id).label("total"),
            func.count(
                case(
                    (
                        Transaction.status == TransactionStatus.PAYED,
                        Transaction.id,
                    )
                )
            ).label("paid"),
            func.count(
                case(
                    (
                        Transaction.status == TransactionStatus.PENDING,
                        Transaction.id,
                    )
                )
            ).label("pending"),
            func.count(
                case(
                    (
                        Transaction.status == TransactionStatus.DEBT,
                        Transaction.id,
                    )
                )
            ).label("debt"),
            func.count(
                case(
                    (
                        Transaction.status == TransactionStatus.RETURNED,
                        Transaction.id,
                    )
                )
            ).label("returned"),
        ).where(
            Transaction.tenant_id == tenant_id,
            Transaction.occurred_at >= start_at,
            Transaction.occurred_at < end_at,
            Transaction.is_reversed.is_(False),
        )
    ).one()

    expense_totals = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            Expense.expense_status == ExpenseStatus.FROM_CAPITAL,
                            Expense.amount,
                        ),
                        else_=ZERO,
                    )
                ),
                ZERO,
            ).label("from_capital"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Expense.expense_status == ExpenseStatus.EXTRA,
                            Expense.amount,
                        ),
                        else_=ZERO,
                    )
                ),
                ZERO,
            ).label("extra"),
        ).where(
            Expense.tenant_id == tenant_id,
            Expense.occurred_at >= start_at,
            Expense.occurred_at < end_at,
        )
    ).one()

    commission = _decimal(transaction_totals.commission)
    from_capital = _decimal(expense_totals.from_capital)
    extra = _decimal(expense_totals.extra)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_commission": commission,
        "total_from_capital_expenses": from_capital,
        "total_extra_expenses": extra,
        "total_profit": commission - from_capital,
        "total_transactions": transaction_totals.total,
        "paid_transactions": transaction_totals.paid,
        "pending_transactions": transaction_totals.pending,
        "debt_transactions": transaction_totals.debt,
        "returned_transactions": transaction_totals.returned,
    }


def get_network_analytics(
    db: Session,
    tenant_id: UUID,
    start_date,
    end_date,
) -> dict:
    start_at, end_at = _utc_range(start_date, end_date)

    statement = (
        select(
            Transaction.network.label("network"),
            func.count(Transaction.id).label("transaction_count"),
            func.count(
                case(
                    (
                        Transaction.status == TransactionStatus.PAYED,
                        Transaction.id,
                    )
                )
            ).label("paid_count"),
            func.coalesce(
                func.sum(Transaction.amount),
                ZERO,
            ).label("total_amount"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Transaction.status == TransactionStatus.PAYED,
                            Transaction.commission,
                        ),
                        else_=ZERO,
                    )
                ),
                ZERO,
            ).label("commission"),
        )
        .where(
            Transaction.tenant_id == tenant_id,
            Transaction.occurred_at >= start_at,
            Transaction.occurred_at < end_at,
            Transaction.is_reversed.is_(False),
        )
        .group_by(Transaction.network)
        .order_by(Transaction.network)
    )

    rows = db.execute(statement).all()

    return {
        "start_date": start_date,
        "end_date": end_date,
        "items": [
            {
                "network": row.network,
                "transaction_count": row.transaction_count,
                "paid_transaction_count": row.paid_count,
                "total_transaction_amount": _decimal(row.total_amount),
                "total_commission": _decimal(row.commission),
            }
            for row in rows
        ],
    }


def get_agent_performance(
    db: Session,
    tenant_id: UUID,
    start_date,
    end_date,
) -> dict:
    start_at, end_at = _utc_range(start_date, end_date)

    statement = (
        select(
            User.id.label("agent_id"),
            User.full_name.label("agent_name"),
            User.agent_number.label("agent_number"),
            func.count(Transaction.id).label("transaction_count"),
            func.count(
                case(
                    (
                        Transaction.status == TransactionStatus.PAYED,
                        Transaction.id,
                    )
                )
            ).label("paid_count"),
            func.count(
                case(
                    (
                        Transaction.status == TransactionStatus.DEBT,
                        Transaction.id,
                    )
                )
            ).label("debt_count"),
            func.coalesce(
                func.sum(Transaction.amount),
                ZERO,
            ).label("total_amount"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Transaction.status == TransactionStatus.PAYED,
                            Transaction.commission,
                        ),
                        else_=ZERO,
                    )
                ),
                ZERO,
            ).label("commission"),
        )
        .join(
            Transaction,
            Transaction.created_by_user_id == User.id,
        )
        .join(
            TenantMember,
            (TenantMember.user_id == User.id) & (TenantMember.tenant_id == Transaction.tenant_id),
        )
        .where(
            Transaction.tenant_id == tenant_id,
            TenantMember.tenant_id == tenant_id,
            Transaction.occurred_at >= start_at,
            Transaction.occurred_at < end_at,
            Transaction.is_reversed.is_(False),
        )
        .group_by(
            User.id,
            User.full_name,
            User.agent_number,
        )
        .order_by(func.count(Transaction.id).desc())
    )

    rows = db.execute(statement).all()

    return {
        "start_date": start_date,
        "end_date": end_date,
        "items": [
            {
                "agent_id": row.agent_id,
                "agent_name": row.agent_name,
                "agent_number": row.agent_number,
                "transaction_count": row.transaction_count,
                "paid_transaction_count": row.paid_count,
                "debt_transaction_count": row.debt_count,
                "total_transaction_amount": _decimal(row.total_amount),
                "total_commission": _decimal(row.commission),
            }
            for row in rows
        ],
    }


def get_debtor_analytics(
    db: Session,
    tenant_id: UUID,
) -> dict:
    statement = select(
        func.count(
            case(
                (
                    Debtor.status == DebtorStatus.PENDING,
                    Debtor.id,
                )
            )
        ).label("pending_count"),
        func.count(
            case(
                (
                    Debtor.status == DebtorStatus.PAID,
                    Debtor.id,
                )
            )
        ).label("paid_count"),
        func.coalesce(
            func.sum(
                case(
                    (
                        Debtor.status == DebtorStatus.PENDING,
                        Debtor.amount,
                    ),
                    else_=ZERO,
                )
            ),
            ZERO,
        ).label("pending_amount"),
        func.coalesce(
            func.sum(
                case(
                    (
                        Debtor.status == DebtorStatus.PAID,
                        Debtor.amount,
                    ),
                    else_=ZERO,
                )
            ),
            ZERO,
        ).label("paid_amount"),
    ).where(Debtor.tenant_id == tenant_id)

    row = db.execute(statement).one()

    return {
        "pending_debtor_count": row.pending_count,
        "paid_debtor_count": row.paid_count,
        "pending_debt_amount": _decimal(row.pending_amount),
        "paid_debt_amount": _decimal(row.paid_amount),
    }


def get_dashboard(
    db: Session,
    tenant_id: UUID,
    business_date,
) -> dict:
    start_at, end_at = _utc_range(
        business_date,
        business_date,
    )

    master_capital = db.scalar(
        select(func.coalesce(func.sum(Account.balance), ZERO)).where(
            Account.tenant_id == tenant_id,
            Account.is_active.is_(True),
        )
    )

    summary = get_financial_summary(
        db=db,
        tenant_id=tenant_id,
        start_date=business_date,
        end_date=business_date,
    )

    debtor_summary = get_debtor_analytics(
        db=db,
        tenant_id=tenant_id,
    )

    return {
        "master_capital": _decimal(master_capital),
        "total_commission": summary["total_commission"],
        "total_from_capital_expenses": summary["total_from_capital_expenses"],
        "total_profit": summary["total_profit"],
        "pending_debt_amount": debtor_summary["pending_debt_amount"],
        "pending_debt_count": debtor_summary["pending_debtor_count"],
        "total_transactions_today": summary["total_transactions"],
        "paid_transactions_today": summary["paid_transactions"],
    }
