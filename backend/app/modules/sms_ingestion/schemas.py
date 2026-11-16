from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.sms_enums import SmsMessageStatus
from app.models.transaction_enums import TransactionNetwork
from pydantic import BaseModel, ConfigDict, Field


class SmsIngestRequest(BaseModel):
    network: TransactionNetwork
    raw_body: str = Field(min_length=1, max_length=10_000)


class SmsIngestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    network: TransactionNetwork
    status: SmsMessageStatus
    parsed_payload: dict[str, Any] | None
    matched_pattern_id: UUID | None
    error_message: str | None
    received_at: datetime
    processed_at: datetime | None
