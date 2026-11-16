from decimal import Decimal
from uuid import UUID

from app.models.financial_enums import AccountType
from pydantic import BaseModel, ConfigDict


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    account_type: AccountType
    balance: Decimal
    is_active: bool


class AccountListResponse(BaseModel):
    items: list[AccountResponse]
    total: int
