from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.models.register_enums import DailyRegisterStatus
from pydantic import BaseModel, ConfigDict


class DailyRegisterOpenRequest(BaseModel):
    business_date: date


class DailyRegisterCloseRequest(BaseModel):
    pass


class DailyRegisterBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    opening_balance: Decimal
    closing_balance: Decimal | None
    captured_at: datetime
    closed_at: datetime | None


class DailyRegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_date: date
    status: DailyRegisterStatus
    opening_master_capital: Decimal
    closing_master_capital: Decimal | None
    opened_at: datetime
    closed_at: datetime | None


class DailyRegisterDetailResponse(DailyRegisterResponse):
    balances: list[DailyRegisterBalanceResponse]


class DailyRegisterListResponse(BaseModel):
    items: list[DailyRegisterResponse]
    total: int
    page: int
    page_size: int
