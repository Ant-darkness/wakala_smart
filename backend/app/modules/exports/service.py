import csv
from collections.abc import Iterator
from datetime import datetime
from io import StringIO
from uuid import UUID

from app.models.expense import Expense
from app.models.transaction import Transaction
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session


def _csv_rows(headers: list[str], rows) -> Iterator[str]:
    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow(headers)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    for row in rows:
        writer.writerow(row)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


def _validate_dates(
    date_from: datetime | None,
    date_to: datetime | None,
) -> None:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail="date_from cannot be later than date_to",
        )

    for value in (date_from, date_to):
        if value and value.tzinfo is None:
            raise HTTPException(
                status_code=422,
                detail="Export dates must include a timezone",
            )


def export_transactions_csv(
    db: Session,
    *,
    tenant_id: UUID,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    _validate_dates(date_from, date_to)

    query = select(Transaction).where(Transaction.tenant_id == tenant_id)

    if date_from:
        query = query.where(Transaction.occurred_at >= date_from)

    if date_to:
        query = query.where(Transaction.occurred_at <= date_to)

    query = query.order_by(
        Transaction.occurred_at.asc(),
        Transaction.id.asc(),
    ).execution_options(yield_per=500)

    result = db.scalars(query)

    def rows():
        for item in result:
            yield (
                str(item.id),
                str(item.reference or ""),
                str(item.network),
                str(item.transaction_type),
                str(item.status),
                str(item.amount),
                str(item.fee),
                str(item.commission),
                item.occurred_at.isoformat(),
                str(item.is_reversed),
            )

    return _csv_rows(
        [
            "transaction_id",
            "reference",
            "network",
            "transaction_type",
            "status",
            "amount",
            "fee",
            "commission",
            "occurred_at",
            "is_reversed",
        ],
        rows(),
    )


def export_expenses_csv(
    db: Session,
    *,
    tenant_id: UUID,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    _validate_dates(date_from, date_to)

    query = select(Expense).where(Expense.tenant_id == tenant_id)

    if date_from:
        query = query.where(Expense.occurred_at >= date_from)

    if date_to:
        query = query.where(Expense.occurred_at <= date_to)

    query = query.order_by(
        Expense.occurred_at.asc(),
        Expense.id.asc(),
    ).execution_options(yield_per=500)

    result = db.scalars(query)

    def rows():
        for item in result:
            yield (
                str(item.id),
                str(item.category_id),
                str(item.account_id),
                str(item.expense_status),
                str(item.amount),
                str(item.description or ""),
                str(item.reference or ""),
                item.occurred_at.isoformat(),
            )

    return _csv_rows(
        [
            "expense_id",
            "category_id",
            "account_id",
            "expense_status",
            "amount",
            "description",
            "reference",
            "occurred_at",
        ],
        rows(),
    )
