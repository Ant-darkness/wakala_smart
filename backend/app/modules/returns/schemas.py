from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from app.models.return_enums import ReturnDirection, ReturnSource
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ReturnReference = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=150),
]

ReturnReason = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=1000),
]


class ReturnCreateRequest(BaseModel):
    transaction_id: UUID | None = None
    reference: ReturnReference
    direction: ReturnDirection
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    reason: ReturnReason


class ReturnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID | None
    reference: str
    direction: ReturnDirection
    amount: Decimal
    reason: str
    source: ReturnSource
    created_at: datetime


class ReturnQueryRequest(BaseModel):
    reference: str | None = Field(default=None, max_length=150)
    direction: ReturnDirection | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ReturnListResponse(BaseModel):
    items: list[ReturnResponse]
    total: int
    page: int
    page_size: int
