from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.financial_enums import AccountType
from pydantic import BaseModel, ConfigDict, Field


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    account_type: AccountType
    balance: Decimal
    is_active: bool


class CapitalMasterResponse(BaseModel):
    tenant_id: UUID
    cash_balance: Decimal
    cashless_balance: Decimal
    master_capital: Decimal
    accounts: list[AccountResponse]


class AccountCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    account_type: AccountType


class CapitalConversionRequest(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    reason: str = Field(min_length=5, max_length=500)


class CapitalInjectionRequest(BaseModel):
    destination_account_id: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    reason: str = Field(min_length=5, max_length=500)


class FloatShiftRequest(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    reason: str = Field(min_length=5, max_length=500)


class CapitalAdjustmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    adjustment_type: str
    amount: Decimal
    master_capital_before: Decimal
    master_capital_after: Decimal
    reference: str
    reason: str
    created_at: datetime


class FinancialHistoryResponse(BaseModel):
    items: list[CapitalAdjustmentResponse]
    total: int
    page: int
    page_size: int
