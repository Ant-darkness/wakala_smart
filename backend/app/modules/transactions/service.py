import hashlib
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.financial_enums import AccountType
from app.models.transaction import Transaction
from app.models.transaction_enums import (
    SyncStatus,
    TransactionNetwork,
    TransactionStatus,
    TransactionType,
)
from app.modules.ledger.postings import post_commission_income
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

GRACE_PERIOD_MINUTES = 5

NETWORK_ACCOUNT_MAP = {
    TransactionNetwork.MPESA: AccountType.MPESA,
    TransactionNetwork.HALOPESA: AccountType.HALOPESA,
    TransactionNetwork.AIRTEL_MONEY: AccountType.AIRTEL_MONEY,
    TransactionNetwork.TIGO_YAS: AccountType.TIGO_YAS,
    TransactionNetwork.CASH: AccountType.CASH,
}


def _normalize_sms(body: str) -> str:
    return re.sub(r"\s+", " ", body.strip()).casefold()


def _generate_sms_fingerprint(
    network: TransactionNetwork,
    reference: str,
    raw_sms_body: str | None,
) -> str:
    normalized_body = _normalize_sms(raw_sms_body) if raw_sms_body else ""

    fingerprint_source = f"{network.value}|{reference.strip().upper()}|{normalized_body}"

    return hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()


def _validate_account(
    db: Session,
    *,
    tenant_id: UUID,
    account_id: UUID,
    network: TransactionNetwork,
) -> Account:
    account = db.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.tenant_id == tenant_id,
        )
    )

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found in this business.",
        )

    if not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected account is inactive.",
        )

    expected_account_type = NETWORK_ACCOUNT_MAP[network]

    if account.account_type != expected_account_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transaction network does not match the selected account.",
        )

    return account


def _initial_status(
    transaction_type: TransactionType,
) -> tuple[TransactionStatus, datetime | None]:

    now = datetime.now(UTC)

    if transaction_type == TransactionType.INCOME:
        return TransactionStatus.PAYED, None

    if transaction_type == TransactionType.EXPENSE:
        return (
            TransactionStatus.PENDING,
            now + timedelta(minutes=5),
        )

    if transaction_type == TransactionType.TRANSFER:
        # Transfer requires its own matching/reconciliation workflow.
        return TransactionStatus.PENDING, None

    raise ValueError("Unsupported transaction type")


def sync_transactions(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    transactions: list,
) -> dict:
    created_transactions: list[Transaction] = []
    duplicates = 0

    try:
        for item in transactions:
            reference = item.reference.strip().upper()

            account = _validate_account(
                db,
                tenant_id=tenant_id,
                account_id=item.account_id,
                network=item.network,
            )

            fingerprint = _generate_sms_fingerprint(
                item.network,
                reference,
                item.raw_sms_body,
            )

            existing = db.scalar(
                select(Transaction.id).where(
                    Transaction.tenant_id == tenant_id,
                    Transaction.network == item.network,
                    Transaction.reference == reference,
                )
            )

            if existing is None:
                existing = db.scalar(
                    select(Transaction.id).where(
                        Transaction.tenant_id == tenant_id,
                        Transaction.sms_fingerprint == fingerprint,
                    )
                )

            if existing is not None:
                duplicates += 1
                continue

            initial_status, grace_expires_at = _initial_status(item.transaction_type)

            transaction = Transaction(
                tenant_id=tenant_id,
                account_id=account.id,
                created_by_user_id=user_id,
                reference=reference,
                amount=item.amount,
                fee=item.fee,
                commission=item.commission,
                transaction_type=item.transaction_type,
                status=initial_status,
                network=item.network,
                raw_sms_body=item.raw_sms_body,
                sms_fingerprint=fingerprint,
                grace_expires_at=grace_expires_at,
                is_pending_debt=False,
                is_reversed=False,
                balance_applied=False,
                occurred_at=item.occurred_at,
                sync_status=SyncStatus.SYNCED,
            )

            try:
                # Transaction and its journal posting must succeed
                # or fail together inside this savepoint.
                with db.begin_nested():
                    db.add(transaction)
                    db.flush()

                    if initial_status == TransactionStatus.PAYED:
                        post_commission_income(
                            db,
                            tenant_id=tenant_id,
                            transaction_id=transaction.id,
                            commission=Decimal(str(transaction.commission or 0)),
                            user_id=user_id,
                        )

                    db.add(
                        AuditLog(
                            actor_user_id=user_id,
                            actor_platform_user_id=None,
                            tenant_id=tenant_id,
                            action="TRANSACTION_CREATED",
                            resource_type="TRANSACTION",
                            resource_id=str(transaction.id),
                            after_data={
                                "reference": reference,
                                "network": item.network.value,
                                "amount": str(item.amount),
                                "status": initial_status.value,
                            },
                        )
                    )

                created_transactions.append(transaction)

            except IntegrityError:
                duplicate = db.scalar(
                    select(Transaction.id).where(
                        Transaction.tenant_id == tenant_id,
                        Transaction.network == item.network,
                        Transaction.reference == reference,
                    )
                )

                if duplicate is not None:
                    duplicates += 1
                    continue

                duplicate = db.scalar(
                    select(Transaction.id).where(
                        Transaction.tenant_id == tenant_id,
                        Transaction.sms_fingerprint == fingerprint,
                    )
                )

                if duplicate is not None:
                    duplicates += 1
                    continue

                raise

        db.commit()

    except Exception:
        db.rollback()
        raise

    for transaction in created_transactions:
        db.refresh(transaction)

    return {
        "received": len(transactions),
        "created": len(created_transactions),
        "duplicates": duplicates,
        "transactions": created_transactions,
    }


def update_transaction_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    transaction_id: UUID,
    new_status: TransactionStatus,
    reason: str,
) -> Transaction:
    try:
        transaction = db.scalar(
            select(Transaction)
            .where(
                Transaction.id == transaction_id,
                Transaction.tenant_id == tenant_id,
            )
            .with_for_update()
        )

        if transaction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )

        allowed_transitions = {
            TransactionStatus.PENDING: {
                TransactionStatus.PAYED,
                TransactionStatus.DEBT,
            },
            TransactionStatus.DEBT: {
                TransactionStatus.PAYED,
            },
        }

        previous_status = transaction.status
        allowed = allowed_transitions.get(previous_status, set())

        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Transition from {previous_status.value} to {new_status.value} is not allowed."
                ),
            )

        transaction.status = new_status
        transaction.is_pending_debt = new_status == TransactionStatus.DEBT

        if new_status == TransactionStatus.PAYED:
            transaction.grace_expires_at = None
            transaction.is_pending_debt = False

            # Post commission exactly once when moving into PAYED.
            post_commission_income(
                db,
                tenant_id=tenant_id,
                transaction_id=transaction.id,
                commission=Decimal(str(transaction.commission or 0)),
                user_id=user_id,
            )

        db.add(
            AuditLog(
                actor_user_id=user_id,
                actor_platform_user_id=None,
                tenant_id=tenant_id,
                action="TRANSACTION_STATUS_CHANGED",
                resource_type="TRANSACTION",
                resource_id=str(transaction.id),
                before_data={
                    "status": previous_status.value,
                },
                after_data={
                    "status": new_status.value,
                },
                reason=reason.strip(),
            )
        )

        db.commit()
        db.refresh(transaction)
        return transaction

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def query_transactions(
    db: Session,
    *,
    tenant_id: UUID,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    transaction_status: TransactionStatus | None = None,
    network: TransactionNetwork | None = None,
    transaction_type: TransactionType | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Transaction], int]:
    filters = [Transaction.tenant_id == tenant_id]

    if start_at:
        filters.append(Transaction.occurred_at >= start_at)

    if end_at:
        filters.append(Transaction.occurred_at <= end_at)

    if transaction_status:
        filters.append(Transaction.status == transaction_status)

    if network:
        filters.append(Transaction.network == network)

    if transaction_type:
        filters.append(Transaction.transaction_type == transaction_type)

    statement = (
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.occurred_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    count_statement = select(func.count(Transaction.id)).where(*filters)

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return items, total
