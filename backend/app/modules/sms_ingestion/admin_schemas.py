from datetime import datetime
from uuid import UUID

import regex
from app.models.transaction_enums import TransactionNetwork
from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_GROUPS = {
    "reference",
    "amount",
    "fee",
    "commission",
    "transaction_type",
    "occurred_at",
}


class SmsPatternCreateRequest(BaseModel):
    network: TransactionNetwork
    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    pattern: str = Field(min_length=1, max_length=2000)
    version: int = Field(default=1, ge=1)
    priority: int = Field(default=100, ge=1, le=1000)

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, value: str) -> str:
        try:
            compiled = regex.compile(value)
        except regex.error as exc:
            raise ValueError("Invalid regular expression.") from exc

        groups = set(compiled.groupindex.keys())

        if not {"reference", "amount"}.issubset(groups):
            raise ValueError("Pattern must capture reference and amount.")

        if groups - ALLOWED_GROUPS:
            raise ValueError("Pattern contains unsupported named groups.")

        return value


class SmsPatternResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    network: TransactionNetwork
    name: str
    description: str | None
    pattern: str
    version: int
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
