from datetime import date
from decimal import Decimal
from uuid import UUID

from app.models.transaction_enums import TransactionNetwork
from pydantic import BaseModel


class AnalyticsDateRange(BaseModel):
    start_date: date
    end_date: date

    def validate_range(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")


class FinancialSummaryResponse(BaseModel):
    start_date: date
    end_date: date

    total_commission: Decimal
    total_from_capital_expenses: Decimal
    total_extra_expenses: Decimal
    total_profit: Decimal

    total_transactions: int
    paid_transactions: int
    pending_transactions: int
    debt_transactions: int
    returned_transactions: int


class NetworkAnalyticsItem(BaseModel):
    network: TransactionNetwork

    transaction_count: int
    paid_transaction_count: int

    total_transaction_amount: Decimal
    total_commission: Decimal


class NetworkAnalyticsResponse(BaseModel):
    start_date: date
    end_date: date
    items: list[NetworkAnalyticsItem]


class AgentPerformanceItem(BaseModel):
    agent_id: UUID
    agent_name: str
    agent_number: str | None

    transaction_count: int
    paid_transaction_count: int
    debt_transaction_count: int

    total_transaction_amount: Decimal
    total_commission: Decimal


class AgentPerformanceResponse(BaseModel):
    start_date: date
    end_date: date
    items: list[AgentPerformanceItem]


class DebtorAnalyticsResponse(BaseModel):
    pending_debtor_count: int
    paid_debtor_count: int
    pending_debt_amount: Decimal
    paid_debt_amount: Decimal


class DashboardResponse(BaseModel):
    master_capital: Decimal
    total_commission: Decimal
    total_from_capital_expenses: Decimal
    total_profit: Decimal

    pending_debt_amount: Decimal
    pending_debt_count: int

    total_transactions_today: int
    paid_transactions_today: int
