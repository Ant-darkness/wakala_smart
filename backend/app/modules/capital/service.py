import secrets
import uuid
from decimal import Decimal
from uuid import UUID

from app.models.account import Account
from app.models.capital_adjustment import CapitalAdjustment
from app.models.financial_enums import (
    AccountType,
    CapitalAdjustmentType,
)
from app.modules.audit.service import record_user_action
from app.modules.ledger.helpers import get_ledger_account
from app.modules.ledger.service import post_journal_entry
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

ZERO = Decimal("0.00")


# ---------------------------------------------------------
# LEDGER ACCOUNT MAPPING
# ---------------------------------------------------------

LEDGER_ACCOUNT_CODES = {
    AccountType.CASH: "1000",
    AccountType.MPESA: "1010",
    AccountType.HALOPESA: "1020",
    AccountType.AIRTEL_MONEY: "1030",
    AccountType.TIGO_YAS: "1040",
}


def _ledger_code_for_account(account: Account) -> str:
    code = LEDGER_ACCOUNT_CODES.get(account.account_type)

    if not code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported financial account type.",
        )

    return code


# ---------------------------------------------------------
# MASTER CAPITAL
# ---------------------------------------------------------


def _master_capital(
    db: Session,
    tenant_id: UUID,
) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(Account.balance), 0)).where(
            Account.tenant_id == tenant_id,
            Account.is_active.is_(True),
        )
    )

    return Decimal(str(value or ZERO))


def get_capital_master(
    db: Session,
    *,
    tenant_id: UUID,
) -> dict:
    accounts = list(
        db.scalars(
            select(Account)
            .where(
                Account.tenant_id == tenant_id,
                Account.is_active.is_(True),
            )
            .order_by(Account.account_type.asc())
        ).all()
    )

    cash_balance = sum(
        (account.balance for account in accounts if account.account_type == AccountType.CASH),
        ZERO,
    )

    cashless_balance = sum(
        (account.balance for account in accounts if account.account_type != AccountType.CASH),
        ZERO,
    )

    return {
        "tenant_id": tenant_id,
        "cash_balance": cash_balance,
        "cashless_balance": cashless_balance,
        "master_capital": cash_balance + cashless_balance,
        "accounts": accounts,
    }


# ---------------------------------------------------------
# CREATE ACCOUNT
# ---------------------------------------------------------


def create_account(
    db: Session,
    *,
    tenant_id: UUID,
    actor_user_id: UUID,
    name: str,
    account_type: AccountType,
) -> Account:

    name = name.strip()

    if len(name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Account name must contain at least 2 characters.",
        )

    ledger_code = LEDGER_ACCOUNT_CODES.get(account_type)

    if not ledger_code:
        raise HTTPException(
            status_code=422,
            detail="Unsupported financial account type.",
        )

    try:
        existing = db.scalar(
            select(Account).where(
                Account.tenant_id == tenant_id,
                Account.account_type == account_type,
            )
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="An account of this type already exists for this business.",
            )

        get_ledger_account(
            db,
            tenant_id=tenant_id,
            code=ledger_code,
            lock=False,
        )

        account = Account(
            tenant_id=tenant_id,
            name=name,
            account_type=account_type,
            balance=ZERO,
            is_active=True,
        )

        db.add(account)
        db.flush()

        record_user_action(
            db,
            user_id=actor_user_id,
            tenant_id=tenant_id,
            action="CAPITAL_ACCOUNT_CREATED",
            resource_type="ACCOUNT",
            resource_id=str(account.id),
            after_data={
                "name": account.name,
                "account_type": account.account_type.value,
                "balance": str(account.balance),
            },
        )

        db.commit()
        db.refresh(account)

        return account

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------
# ACCOUNT LOCKING
# ---------------------------------------------------------


def _lock_accounts(
    db: Session,
    *,
    tenant_id: UUID,
    account_ids: list[UUID],
) -> dict[UUID, Account]:
    unique_ids = sorted(set(account_ids), key=str)

    accounts = list(
        db.scalars(
            select(Account)
            .where(
                Account.tenant_id == tenant_id,
                Account.id.in_(unique_ids),
            )
            .order_by(Account.id)
            .with_for_update()
        ).all()
    )

    result = {account.id: account for account in accounts}

    if len(result) != len(unique_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=("One or more accounts were not found in this business."),
        )

    if any(not account.is_active for account in accounts):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account is inactive.",
        )

    return result


# ---------------------------------------------------------
# AMOUNT VALIDATION
# ---------------------------------------------------------


def _validate_amount(amount: Decimal) -> None:
    if not amount.is_finite() or amount <= ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Amount must be a positive finite value.",
        )

    if amount.as_tuple().exponent < -2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=("Amount cannot have more than two decimal places."),
        )


# ---------------------------------------------------------
# REFERENCES
# ---------------------------------------------------------


def _new_reference() -> str:
    return f"CAP-{secrets.token_hex(12).upper()}"


# ---------------------------------------------------------
# SAVE CAPITAL ADJUSTMENT AND AUDIT
# ---------------------------------------------------------


def _save_adjustment(
    db: Session,
    *,
    tenant_id: UUID,
    actor_user_id: UUID,
    source: Account | None,
    destination: Account,
    adjustment_type: CapitalAdjustmentType,
    amount: Decimal,
    master_before: Decimal,
    master_after: Decimal,
    reason: str,
) -> CapitalAdjustment:

    adjustment = CapitalAdjustment(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        source_account_id=source.id if source else None,
        destination_account_id=destination.id,
        adjustment_type=adjustment_type,
        amount=amount,
        master_capital_before=master_before,
        master_capital_after=master_after,
        reference=_new_reference(),
        reason=reason.strip(),
        created_by_user_id=actor_user_id,
    )

    db.add(adjustment)
    db.flush()

    record_user_action(
        db,
        user_id=actor_user_id,
        tenant_id=tenant_id,
        action=f"CAPITAL_{adjustment_type.value}",
        resource_type="CAPITAL_ADJUSTMENT",
        resource_id=str(adjustment.id),
        before_data={
            "master_capital": str(master_before),
        },
        after_data={
            "master_capital": str(master_after),
            "adjustment_amount": str(amount),
            "destination_account_id": str(destination.id),
            "source_account_id": (str(source.id) if source else None),
        },
        reason=reason.strip(),
    )

    return adjustment


# ---------------------------------------------------------
# CAPITAL CONVERSION: CASH -> CASHLESS
# ---------------------------------------------------------


def convert_capital(
    db: Session,
    *,
    tenant_id: UUID,
    actor_user_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
    amount: Decimal,
    reason: str,
) -> CapitalAdjustment:

    _validate_amount(amount)

    if source_account_id == destination_account_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=("Source and destination accounts must be different."),
        )

    try:
        accounts = _lock_accounts(
            db,
            tenant_id=tenant_id,
            account_ids=[
                source_account_id,
                destination_account_id,
            ],
        )

        source = accounts[source_account_id]
        destination = accounts[destination_account_id]

        if source.account_type != AccountType.CASH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=("Capital conversion must start from the CASH account."),
            )

        if destination.account_type == AccountType.CASH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Destination must be a cashless account.",
            )

        if source.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient cash balance.",
            )

        master_before = _master_capital(db, tenant_id)

        source.balance -= amount
        destination.balance += amount

        adjustment = _save_adjustment(
            db,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            source=source,
            destination=destination,
            adjustment_type=CapitalAdjustmentType.FROM_CASH,
            amount=amount,
            master_before=master_before,
            master_after=master_before,
            reason=reason,
        )

        cash_ledger = get_ledger_account(
            db,
            tenant_id=tenant_id,
            code="1000",
            lock=False,
        )

        destination_ledger = get_ledger_account(
            db,
            tenant_id=tenant_id,
            code=_ledger_code_for_account(destination),
            lock=False,
        )

        post_journal_entry(
            db,
            tenant_id=tenant_id,
            source_type="CAPITAL_CONVERSION",
            source_id=str(adjustment.id),
            description="Cash to cashless capital conversion",
            created_by_user_id=actor_user_id,
            lines=[
                {
                    "ledger_account_id": destination_ledger.id,
                    "debit": amount,
                    "credit": ZERO,
                },
                {
                    "ledger_account_id": cash_ledger.id,
                    "debit": ZERO,
                    "credit": amount,
                },
            ],
        )

        db.commit()
        db.refresh(adjustment)

        return adjustment

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------
# CAPITAL INJECTION: OUTSIDE CAPITAL -> BUSINESS ASSET
# ---------------------------------------------------------


def inject_capital(
    db: Session,
    *,
    tenant_id: UUID,
    actor_user_id: UUID,
    destination_account_id: UUID,
    amount: Decimal,
    reason: str,
) -> CapitalAdjustment:

    _validate_amount(amount)

    try:
        accounts = _lock_accounts(
            db,
            tenant_id=tenant_id,
            account_ids=[destination_account_id],
        )

        destination = accounts[destination_account_id]

        master_before = _master_capital(db, tenant_id)

        destination.balance += amount

        master_after = master_before + amount

        adjustment = _save_adjustment(
            db,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            source=None,
            destination=destination,
            adjustment_type=CapitalAdjustmentType.OUTSIDE_CAPITAL,
            amount=amount,
            master_before=master_before,
            master_after=master_after,
            reason=reason,
        )

        destination_ledger = get_ledger_account(
            db,
            tenant_id=tenant_id,
            code=_ledger_code_for_account(destination),
            lock=False,
        )

        owner_capital_ledger = get_ledger_account(
            db,
            tenant_id=tenant_id,
            code="3000",
            lock=False,
        )

        post_journal_entry(
            db,
            tenant_id=tenant_id,
            source_type="CAPITAL_INJECTION",
            source_id=str(adjustment.id),
            description="Outside capital injection",
            created_by_user_id=actor_user_id,
            lines=[
                {
                    "ledger_account_id": destination_ledger.id,
                    "debit": amount,
                    "credit": ZERO,
                },
                {
                    "ledger_account_id": owner_capital_ledger.id,
                    "debit": ZERO,
                    "credit": amount,
                },
            ],
        )

        db.commit()
        db.refresh(adjustment)

        return adjustment

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------
# FLOAT SHIFT: CASHLESS -> CASHLESS
# ---------------------------------------------------------


def shift_float(
    db: Session,
    *,
    tenant_id: UUID,
    actor_user_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
    amount: Decimal,
    reason: str,
) -> CapitalAdjustment:

    _validate_amount(amount)

    if source_account_id == destination_account_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=("Source and destination accounts must be different."),
        )

    try:
        accounts = _lock_accounts(
            db,
            tenant_id=tenant_id,
            account_ids=[
                source_account_id,
                destination_account_id,
            ],
        )

        source = accounts[source_account_id]
        destination = accounts[destination_account_id]

        if source.account_type == AccountType.CASH or destination.account_type == AccountType.CASH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=("Float shift is only allowed between cashless accounts."),
            )

        if source.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient source float.",
            )

        master_before = _master_capital(db, tenant_id)

        source.balance -= amount
        destination.balance += amount

        adjustment = _save_adjustment(
            db,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            source=source,
            destination=destination,
            adjustment_type=CapitalAdjustmentType.FLOAT_SHIFT,
            amount=amount,
            master_before=master_before,
            master_after=master_before,
            reason=reason,
        )

        source_ledger = get_ledger_account(
            db,
            tenant_id=tenant_id,
            code=_ledger_code_for_account(source),
            lock=False,
        )

        destination_ledger = get_ledger_account(
            db,
            tenant_id=tenant_id,
            code=_ledger_code_for_account(destination),
            lock=False,
        )

        post_journal_entry(
            db,
            tenant_id=tenant_id,
            source_type="FLOAT_SHIFT",
            source_id=str(adjustment.id),
            description="Float transfer between network accounts",
            created_by_user_id=actor_user_id,
            lines=[
                {
                    "ledger_account_id": destination_ledger.id,
                    "debit": amount,
                    "credit": ZERO,
                },
                {
                    "ledger_account_id": source_ledger.id,
                    "debit": ZERO,
                    "credit": amount,
                },
            ],
        )

        db.commit()
        db.refresh(adjustment)

        return adjustment

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------
# CAPITAL HISTORY
# ---------------------------------------------------------


def get_capital_history(
    db: Session,
    *,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CapitalAdjustment], int]:

    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid pagination parameters.",
        )

    statement = (
        select(CapitalAdjustment)
        .where(CapitalAdjustment.tenant_id == tenant_id)
        .order_by(CapitalAdjustment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    total = (
        db.scalar(
            select(func.count(CapitalAdjustment.id)).where(CapitalAdjustment.tenant_id == tenant_id)
        )
        or 0
    )

    return list(db.scalars(statement).all()), total
