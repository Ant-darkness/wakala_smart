from uuid import UUID

from app.models.ledger import LedgerAccount
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_ledger_account(
    db: Session,
    *,
    tenant_id: UUID,
    code: str,
    lock: bool = True,
) -> LedgerAccount:
    query = select(LedgerAccount).where(
        LedgerAccount.tenant_id == tenant_id,
        LedgerAccount.code == code,
        LedgerAccount.is_active.is_(True),
    )

    if lock:
        query = query.with_for_update()

    account = db.scalar(query)

    if not account:
        raise HTTPException(
            status_code=409,
            detail=f"Ledger account {code} is not configured",
        )

    return account
