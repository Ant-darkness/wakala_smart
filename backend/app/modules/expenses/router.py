from app.db.session import get_db
from app.modules.expenses.schemas import (
    CategoryCreateRequest,
    CategoryListResponse,
    CategoryResponse,
    ExpenseCreateRequest,
    ExpenseListResponse,
    ExpenseQueryRequest,
    ExpenseResponse,
)
from app.modules.expenses.service import (
    create_category,
    create_expense,
    list_categories,
    list_expenses,
)
from app.modules.security_tokens.dependencies import (
    require_security_token,
)
from app.modules.tenants.dependencies import (
    get_current_tenant_member,
    require_permission,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"],
)


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=201,
)
def create_category_endpoint(
    payload: CategoryCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("expenses.categories.create")),
):
    return create_category(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )


@router.get(
    "/categories",
    response_model=CategoryListResponse,
)
def list_categories_endpoint(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("expenses.read")),
):
    return list_categories(
        db=db,
        tenant_id=membership.tenant_id,
        include_inactive=include_inactive,
    )


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=201,
)
def create_expense_endpoint(
    payload: ExpenseCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_security_token),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("expenses.create")),
):
    return create_expense(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        category_id=payload.category_id,
        account_id=payload.account_id,
        amount=payload.amount,
        expense_status=payload.expense_status,
        description=payload.description,
        occurred_at=payload.occurred_at,
    )


@router.post(
    "/query",
    response_model=ExpenseListResponse,
)
def query_expenses_endpoint(
    payload: ExpenseQueryRequest,
    db: Session = Depends(get_db),
    membership=Depends(get_current_tenant_member),
    _permission=Depends(require_permission("expenses.read")),
):
    return list_expenses(
        db=db,
        tenant_id=membership.tenant_id,
        query=payload,
    )
