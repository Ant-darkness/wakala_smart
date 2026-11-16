from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.transaction_enums import (
    SyncStatus,
    TransactionNetwork,
    TransactionStatus,
    TransactionType,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TransactionCreateRequest(BaseModel):
    account_id: UUID
    reference: str = Field(min_length=2, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    fee: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=18,
        decimal_places=2,
    )

    commission: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=18,
        decimal_places=2,
    )
    transaction_type: TransactionType
    network: TransactionNetwork
    occurred_at: datetime
    raw_sms_body: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def validate_timestamp(self):
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must include a timezone.")
        return self


class TransactionSyncRequest(BaseModel):
    transactions: list[TransactionCreateRequest] = Field(
        min_length=1,
        max_length=100,
    )


class TransactionStatusUpdateRequest(BaseModel):
    status: TransactionStatus
    reason: str = Field(min_length=5, max_length=500)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    reference: str
    amount: Decimal
    fee: Decimal
    commission: Decimal
    transaction_type: TransactionType
    status: TransactionStatus
    network: TransactionNetwork
    occurred_at: datetime
    grace_expires_at: datetime | None
    is_pending_debt: bool
    is_reversed: bool
    sync_status: SyncStatus


class TransactionSyncResponse(BaseModel):
    received: int
    created: int
    duplicates: int
    transactions: list[TransactionResponse]


class TransactionQueryRequest(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: TransactionStatus | None = None
    network: TransactionNetwork | None = None
    transaction_type: TransactionType | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.start_at and self.end_at and self.end_at < self.start_at:
            raise ValueError("end_at must not be earlier than start_at.")
        return self


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
