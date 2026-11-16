from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from app.models.debtor_enums import DebtorStatus
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

DebtorName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=150),
]

DebtorPhone = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=7, max_length=30),
]


class DebtorCreateRequest(BaseModel):
    transaction_id: UUID
    debtor_name: DebtorName
    debtor_phone: DebtorPhone | None = None
    promised_at: datetime | None = None
    reminder_enabled: bool = False


class DebtorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    reference: str
    debtor_name: str
    debtor_phone: str | None
    amount: Decimal
    promised_at: datetime | None
    status: DebtorStatus
    reminder_enabled: bool
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DebtorListResponse(BaseModel):
    items: list[DebtorResponse]
    total: int
    page: int
    page_size: int


class DebtorQueryRequest(BaseModel):
    status: DebtorStatus | None = None
    search: str | None = Field(default=None, max_length=150)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class DebtorPaymentResponse(BaseModel):
    debtor: DebtorResponse
    transaction_status: str
    message: str
