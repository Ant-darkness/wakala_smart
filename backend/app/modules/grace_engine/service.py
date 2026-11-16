from datetime import UTC, datetime

from app.models.system_event import SystemEvent
from app.models.transaction import Transaction
from app.models.transaction_enums import (
    TransactionStatus,
    TransactionType,
)
from app.modules.ledger.postings import post_commission_income
from sqlalchemy import select
from sqlalchemy.orm import Session


def process_expired_transactions(
    db: Session,
    batch_size: int = 100,
    now: datetime | None = None,
) -> dict[str, int]:
    """
    Automatically changes expired outgoing PENDING transactions
    to PAYED.

    Only EXPENSE transactions are processed.
    DEBT, INCOME, TRANSFER and reversed transactions are excluded.
    """

    if batch_size < 1 or batch_size > 1000:
        raise ValueError("batch_size must be between 1 and 1000")

    processing_time = now or datetime.now(UTC)

    if processing_time.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    processed_count = 0

    try:
        statement = (
            select(Transaction)
            .where(
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.status == TransactionStatus.PENDING,
                Transaction.grace_expires_at.is_not(None),
                Transaction.grace_expires_at <= processing_time,
                Transaction.is_reversed.is_(False),
            )
            .order_by(Transaction.grace_expires_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )

        expired_transactions = list(db.scalars(statement).all())

        for transaction in expired_transactions:
            # Recheck the conditions while holding the row lock.
            if transaction.status != TransactionStatus.PENDING:
                continue

            if transaction.is_reversed:
                continue

            if (
                transaction.grace_expires_at is None
                or transaction.grace_expires_at > processing_time
            ):
                continue

            old_status = transaction.status.value

            transaction.status = TransactionStatus.PAYED
            transaction.grace_expires_at = None
            transaction.is_pending_debt = False

            post_commission_income(
                db,
                tenant_id=transaction.tenant_id,
                commission=transaction.commission,
                user_id=transaction.created_by_user_id,
            )

            db.add(
                SystemEvent(
                    tenant_id=transaction.tenant_id,
                    event_type="TRANSACTION_GRACE_EXPIRED",
                    aggregate_type="TRANSACTION",
                    aggregate_id=str(transaction.id),
                    details={
                        "previous_status": old_status,
                        "new_status": TransactionStatus.PAYED.value,
                        "reason": "Five-minute grace period expired",
                        "processed_at": processing_time.isoformat(),
                    },
                )
            )

            processed_count += 1

        db.commit()

        return {
            "checked": len(expired_transactions),
            "processed": processed_count,
        }

    except Exception:
        db.rollback()
        raise
