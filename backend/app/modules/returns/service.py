from uuid import UUID

from app.models.return_enums import ReturnDirection, ReturnSource
from app.models.returned_transaction import ReturnedTransaction
from app.models.transaction import Transaction
from app.modules.audit.service import record_user_action
from app.modules.returns.schemas import ReturnQueryRequest
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def create_manual_return(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    transaction_id: UUID | None,
    reference: str,
    direction: ReturnDirection,
    amount,
    reason: str,
) -> ReturnedTransaction:
    try:
        transaction = None

        if transaction_id is not None:
            transaction = db.scalar(
                select(Transaction).where(
                    Transaction.id == transaction_id,
                    Transaction.tenant_id == tenant_id,
                )
            )

            if transaction is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Linked transaction not found",
                )

            if transaction.reference != reference:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Return reference does not match linked transaction",
                )

        returned = ReturnedTransaction(
            tenant_id=tenant_id,
            transaction_id=transaction.id if transaction else None,
            reference=reference,
            direction=direction,
            amount=amount,
            reason=reason,
            source=ReturnSource.MANUAL,
            created_by_user_id=user_id,
        )

        db.add(returned)
        db.flush()

        record_user_action(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            action="RETURNED_TRANSACTION_CREATED",
            resource_type="RETURNED_TRANSACTION",
            resource_id=str(returned.id),
            after_data={
                "reference": reference,
                "direction": direction.value,
                "amount": str(amount),
                "source": ReturnSource.MANUAL.value,
                "transaction_id": (str(transaction.id) if transaction else None),
            },
        )

        db.commit()
        db.refresh(returned)

        return returned

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def query_returns(
    db: Session,
    tenant_id: UUID,
    query: ReturnQueryRequest,
) -> dict:
    statement = select(ReturnedTransaction).where(ReturnedTransaction.tenant_id == tenant_id)

    if query.reference:
        statement = statement.where(
            ReturnedTransaction.reference.ilike(f"%{query.reference.strip()}%")
        )

    if query.direction is not None:
        statement = statement.where(ReturnedTransaction.direction == query.direction)

    total_statement = select(func.count()).select_from(statement.order_by(None).subquery())

    total = db.scalar(total_statement) or 0

    items_statement = (
        statement.order_by(ReturnedTransaction.created_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )

    items = list(db.scalars(items_statement).all())

    return {
        "items": items,
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
    }
