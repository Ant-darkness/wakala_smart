from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DailyArchiveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    register_id: UUID
    business_date: date

    opening_master_capital: Decimal
    closing_master_capital: Decimal

    total_transactions: int
    paid_transactions: int
    pending_transactions: int
    debt_transactions: int
    returned_transactions: int

    total_commission: Decimal
    capital_expenses: Decimal
    extra_expenses: Decimal
    net_profit: Decimal

    account_balances: dict
    transaction_summary: dict
    expense_summary: dict


class DailyArchiveListResponse(BaseModel):
    items: list[DailyArchiveResponse]
    total: int
    page: int
    page_size: int
