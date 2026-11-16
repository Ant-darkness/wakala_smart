from uuid import UUID

from app.models.account import Account
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def list_accounts(
    db: Session,
    *,
    tenant_id: UUID,
    include_inactive: bool = False,
) -> tuple[list[Account], int]:

    conditions = [
        Account.tenant_id == tenant_id,
    ]

    if not include_inactive:
        conditions.append(Account.is_active.is_(True))

    total = db.scalar(select(func.count(Account.id)).where(*conditions)) or 0

    accounts = db.scalars(
        select(Account).where(*conditions).order_by(Account.account_type.asc())
    ).all()

    return list(accounts), total


def get_account(
    db: Session,
    *,
    tenant_id: UUID,
    account_id: UUID,
) -> Account | None:

    return db.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.tenant_id == tenant_id,
        )
    )
