from datetime import UTC
from decimal import Decimal
from uuid import UUID

from app.models.account import Account
from app.models.category import Category
from app.models.expense import Expense
from app.models.financial_enums import AccountType, ExpenseStatus
from app.modules.audit.service import record_user_action
from app.modules.expenses.schemas import ExpenseQueryRequest
from app.modules.ledger.postings import post_capital_expense
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def create_expense(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    category_id: UUID,
    account_id: UUID,
    amount,
    expense_status: ExpenseStatus,
    description: str | None,
    occurred_at,
) -> Expense:
    if occurred_at.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="occurred_at must include a timezone",
        )

    try:
        amount = Decimal(str(amount))

        if not amount.is_finite() or amount <= 0:
            raise HTTPException(
                status_code=422,
                detail="Expense amount must be greater than zero.",
            )
        if amount.as_tuple().exponent < -2:
            raise HTTPException(
                status_code=422,
                detail="Expense amount cannot have more than two decimal places.",
            )

        category = db.scalar(
            select(Category)
            .where(
                Category.id == category_id,
                Category.tenant_id == tenant_id,
            )
            .with_for_update()
        )

        if category is None or not category.is_active:
            raise HTTPException(
                status_code=404,
                detail="Active category not found.",
            )

        account = db.scalar(
            select(Account)
            .where(
                Account.id == account_id,
                Account.tenant_id == tenant_id,
            )
            .with_for_update()
        )

        if account is None or not account.is_active:
            raise HTTPException(
                status_code=404,
                detail="Active account not found.",
            )

        # Only FROM_CAPITAL expenses reduce business capital.
        if expense_status == ExpenseStatus.FROM_CAPITAL:
            if account.balance < amount:
                raise HTTPException(
                    status_code=409,
                    detail="Insufficient account balance.",
                )

        expense = Expense(
            tenant_id=tenant_id,
            category_id=category.id,
            account_id=account.id,
            created_by_user_id=user_id,
            amount=amount,
            expense_status=expense_status,
            description=description,
            occurred_at=occurred_at.astimezone(UTC),
        )

        db.add(expense)
        db.flush()

        if expense_status == ExpenseStatus.FROM_CAPITAL:
            account.balance -= amount

            ledger_account_codes = {
                AccountType.CASH: "1000",
                AccountType.MPESA: "1010",
                AccountType.HALOPESA: "1020",
                AccountType.AIRTEL_MONEY: "1030",
                AccountType.TIGO_YAS: "1040",
            }

            payment_ledger_code = ledger_account_codes.get(account.account_type)

            if payment_ledger_code is None:
                raise HTTPException(
                    status_code=422,
                    detail="Unsupported account type for capital expense.",
                )

            post_capital_expense(
                db,
                tenant_id=tenant_id,
                expense_id=expense.id,
                payment_ledger_code=payment_ledger_code,
                amount=amount,
                user_id=user_id,
            )

        record_user_action(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            action="EXPENSE_CREATED",
            resource_type="EXPENSE",
            resource_id=str(expense.id),
            after_data={
                "category_id": str(category.id),
                "account_id": str(account.id),
                "amount": str(amount),
                "expense_status": expense_status.value,
                "occurred_at": occurred_at.isoformat(),
            },
        )

        db.commit()
        db.refresh(expense)
        return expense

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def list_expenses(
    db: Session,
    tenant_id: UUID,
    query: ExpenseQueryRequest,
) -> dict:
    statement = select(Expense).where(Expense.tenant_id == tenant_id)

    if query.category_id:
        statement = statement.where(Expense.category_id == query.category_id)

    if query.expense_status:
        statement = statement.where(Expense.expense_status == query.expense_status)

    if query.start_at:
        if query.start_at.tzinfo is None:
            raise HTTPException(
                status_code=422,
                detail="start_at must include a timezone",
            )
        statement = statement.where(Expense.occurred_at >= query.start_at)

    if query.end_at:
        if query.end_at.tzinfo is None:
            raise HTTPException(
                status_code=422,
                detail="end_at must include a timezone",
            )
        statement = statement.where(Expense.occurred_at <= query.end_at)

    if query.start_at and query.end_at and query.start_at > query.end_at:
        raise HTTPException(
            status_code=422,
            detail="start_at cannot be after end_at",
        )

    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0

    items = list(
        db.scalars(
            statement.order_by(Expense.occurred_at.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        ).all()
    )

    return {
        "items": items,
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
    }


def create_category(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    name: str,
    description: str | None,
) -> Category:
    try:
        existing = db.scalar(
            select(Category.id).where(
                Category.tenant_id == tenant_id,
                func.lower(Category.name) == name.lower(),
            )
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Category already exists",
            )

        category = Category(
            tenant_id=tenant_id,
            name=name,
            description=description,
        )

        db.add(category)
        db.flush()

        record_user_action(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            action="EXPENSE_CATEGORY_CREATED",
            resource_type="CATEGORY",
            resource_id=str(category.id),
            after_data={
                "name": name,
                "description": description,
            },
        )

        db.commit()
        db.refresh(category)
        return category

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def list_categories(
    db: Session,
    tenant_id: UUID,
    include_inactive: bool = False,
) -> dict:
    statement = select(Category).where(Category.tenant_id == tenant_id)

    if not include_inactive:
        statement = statement.where(Category.is_active.is_(True))

    items = list(db.scalars(statement.order_by(Category.name.asc())).all())

    return {
        "items": items,
        "total": len(items),
    }
