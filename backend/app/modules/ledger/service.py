
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.models.ledger import JournalEntry, JournalLine, LedgerAccount
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session


def post_journal_entry(
    db: Session,
    *,
    tenant_id: UUID,
    source_type: str,
    source_id: str,
    description: str,
    lines: list[dict],
    created_by_user_id: UUID | None = None,
) -> JournalEntry:
    source_type = source_type.strip().upper()
    source_id = source_id.strip()
    description = description.strip()

    if not source_type or not source_id or not description:
        raise HTTPException(
            status_code=422,
            detail="Journal source and description are required.",
        )

    if len(source_type) > 40 or len(source_id) > 100 or len(description) > 255:
        raise HTTPException(
            status_code=422,
            detail="Journal source or description exceeds its maximum length.",
        )

    if not isinstance(lines, list) or len(lines) < 2:
        raise HTTPException(
            status_code=422,
            detail="A journal requires at least two lines.",
        )

    existing_entry = db.scalar(
        select(JournalEntry.id).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.source_type == source_type,
            JournalEntry.source_id == source_id,
        )
    )

    if existing_entry:
        raise HTTPException(
            status_code=409,
            detail="This financial operation is already posted.",
        )

    debit_total = Decimal("0.00")
    credit_total = Decimal("0.00")
    normalized_lines: list[dict] = []
    account_ids: set[UUID] = set()

    for line in lines:
        if not isinstance(line, dict):
            raise HTTPException(
                status_code=422,
                detail="Each journal line must be an object.",
            )

        account_id = line.get("ledger_account_id")

        if not isinstance(account_id, UUID):
            raise HTTPException(
                status_code=422,
                detail="Invalid ledger account ID.",
            )

        try:
            debit = Decimal(str(line.get("debit", 0)))
            credit = Decimal(str(line.get("credit", 0)))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail="Journal amounts must be valid decimal numbers.",
            ) from exc

        if not debit.is_finite() or not credit.is_finite():
            raise HTTPException(
                status_code=422,
                detail="Journal amounts must be finite numbers.",
            )

        if (
            debit.as_tuple().exponent < -2
            or credit.as_tuple().exponent < -2
        ):
            raise HTTPException(
                status_code=422,
                detail="Journal amounts cannot exceed two decimal places.",
            )

        if debit < 0 or credit < 0:
            raise HTTPException(
                status_code=422,
                detail="Journal amounts cannot be negative.",
            )

        if (debit > 0) == (credit > 0):
            raise HTTPException(
                status_code=422,
                detail="Each journal line must contain either debit or credit.",
            )

        memo = line.get("memo")
        if memo is not None:
            if not isinstance(memo, str):
                raise HTTPException(
                    status_code=422,
                    detail="Journal line memo must be text.",
                )
            memo = memo.strip() or None

        debit_total += debit
        credit_total += credit
        account_ids.add(account_id)

        normalized_lines.append(
            {
                "ledger_account_id": account_id,
                "debit": debit,
                "credit": credit,
                "memo": memo,
            }
        )

    if debit_total <= 0 or debit_total != credit_total:
        raise HTTPException(
            status_code=422,
            detail="Journal debits and credits must be equal and greater than zero.",
        )

    accounts = db.scalars(
        select(LedgerAccount)
        .where(
            LedgerAccount.tenant_id == tenant_id,
            LedgerAccount.id.in_(account_ids),
            LedgerAccount.is_active.is_(True),
        )
        .order_by(LedgerAccount.id)
        .with_for_update()
    ).all()

    if {account.id for account in accounts} != account_ids:
        raise HTTPException(
            status_code=422,
            detail="One or more ledger accounts are invalid for this tenant.",
        )

    entry = JournalEntry(
        tenant_id=tenant_id,
        source_type=source_type,
        source_id=source_id,
        description=description,
        created_by_user_id=created_by_user_id,
    )

    db.add(entry)
    db.flush()

    for line in normalized_lines:
        db.add(
            JournalLine(
                tenant_id=tenant_id,
                journal_entry_id=entry.id,
                ledger_account_id=line["ledger_account_id"],
                debit=line["debit"],
                credit=line["credit"],
                memo=line["memo"],
            )
        )

    db.flush()
    return entry
