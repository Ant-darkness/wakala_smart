from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from app.models.financial_enums import ExpenseStatus
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

CategoryName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=100,
    ),
]

ExpenseDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=1000,
    ),
]


class CategoryCreateRequest(BaseModel):
    name: CategoryName
    description: str | None = Field(default=None, max_length=500)


class CategoryUpdateRequest(BaseModel):
    name: CategoryName | None = None
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]
    total: int


class ExpenseCreateRequest(BaseModel):
    category_id: UUID
    account_id: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    expense_status: ExpenseStatus
    description: ExpenseDescription | None = None
    occurred_at: datetime


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    account_id: UUID
    register_id: UUID | None
    amount: Decimal
    expense_status: ExpenseStatus
    description: str | None
    reference: str | None
    occurred_at: datetime
    created_at: datetime


class ExpenseQueryRequest(BaseModel):
    category_id: UUID | None = None
    expense_status: ExpenseStatus | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ExpenseListResponse(BaseModel):
    items: list[ExpenseResponse]
    total: int
    page: int
    page_size: int
