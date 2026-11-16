from datetime import UTC, datetime
from uuid import UUID

from app.models.debtor import Debtor
from app.models.debtor_enums import DebtorStatus
from app.models.transaction import Transaction
from app.models.transaction_enums import (
    TransactionStatus,
    TransactionType,
)
from app.modules.audit.service import record_user_action
from app.modules.debtors.schemas import DebtorQueryRequest
from app.modules.ledger.postings import post_commission_income
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def create_debtor(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    transaction_id: UUID,
    debtor_name: str,
    debtor_phone: str | None = None,
    promised_at: datetime | None = None,
    reminder_enabled: bool = False,
) -> Debtor:
    if promised_at is not None and promised_at.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="promised_at must include a timezone",
        )

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
                detail="Transaction not found",
            )

        if transaction.transaction_type != TransactionType.EXPENSE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only outgoing transactions can become debts",
            )

        if transaction.is_reversed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A reversed transaction cannot become a debt",
            )

        if transaction.status != TransactionStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only PENDING transactions can be marked as DEBT",
            )

        existing = db.scalar(
            select(Debtor.id).where(
                Debtor.tenant_id == tenant_id,
                Debtor.transaction_id == transaction_id,
            )
        )

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A debtor record already exists for this transaction",
            )

        debtor = Debtor(
            tenant_id=tenant_id,
            transaction_id=transaction.id,
            reference=transaction.reference,
            debtor_name=debtor_name,
            debtor_phone=debtor_phone,
            amount=transaction.amount,
            promised_at=promised_at,
            reminder_enabled=reminder_enabled,
            status=DebtorStatus.PENDING,
        )

        transaction.status = TransactionStatus.DEBT
        transaction.is_pending_debt = True
        transaction.grace_expires_at = None

        db.add(debtor)
        db.flush()

        record_user_action(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            action="DEBTOR_CREATED",
            resource_type="DEBTOR",
            resource_id=str(debtor.id),
            after_data={
                "transaction_id": str(transaction.id),
                "reference": transaction.reference,
                "amount": str(transaction.amount),
                "status": DebtorStatus.PENDING.value,
            },
        )

        db.commit()
        db.refresh(debtor)

        return debtor

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A debtor record already exists for this transaction",
        )

    except Exception:
        db.rollback()
        raise


def pay_debtor(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    debtor_id: UUID,
) -> Debtor:
    try:
        debtor = db.scalar(
            select(Debtor)
            .where(
                Debtor.id == debtor_id,
                Debtor.tenant_id == tenant_id,
            )
            .with_for_update()
        )

        if debtor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debtor record not found",
            )

        if debtor.status == DebtorStatus.PAID:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This debt has already been paid",
            )

        transaction = db.scalar(
            select(Transaction)
            .where(
                Transaction.id == debtor.transaction_id,
                Transaction.tenant_id == tenant_id,
            )
            .with_for_update()
        )

        if transaction is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The linked transaction could not be found",
            )

        if transaction.status != TransactionStatus.DEBT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The linked transaction is not in DEBT status",
            )

        if transaction.is_reversed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A reversed transaction cannot be paid",
            )

        now = datetime.now(UTC)

        debtor.status = DebtorStatus.PAID
        debtor.paid_at = now

        transaction.status = TransactionStatus.PAYED
        transaction.is_pending_debt = False
        transaction.grace_expires_at = None

        post_commission_income(
            db,
            tenant_id=tenant_id,
            transaction_id=transaction.id,
            commission=transaction.commission,
            user_id=user_id,
        )

        record_user_action(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            action="DEBTOR_PAID",
            resource_type="DEBTOR",
            resource_id=str(debtor.id),
            before_data={
                "debtor_status": DebtorStatus.PENDING.value,
                "transaction_status": TransactionStatus.DEBT.value,
            },
            after_data={
                "debtor_status": DebtorStatus.PAID.value,
                "transaction_status": TransactionStatus.PAYED.value,
                "paid_at": now.isoformat(),
            },
        )

        db.commit()
        db.refresh(debtor)

        return debtor

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def list_debtors(
    db: Session,
    tenant_id: UUID,
    query: DebtorQueryRequest,
) -> dict:
    statement = select(Debtor).where(Debtor.tenant_id == tenant_id)

    if query.status is not None:
        statement = statement.where(Debtor.status == query.status)

    if query.search:
        search_term = f"%{query.search.strip()}%"

        statement = statement.where(
            or_(
                Debtor.debtor_name.ilike(search_term),
                Debtor.debtor_phone.ilike(search_term),
                Debtor.reference.ilike(search_term),
            )
        )

    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())

    total = db.scalar(count_statement) or 0

    items_statement = (
        statement.order_by(Debtor.created_at.desc())
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
