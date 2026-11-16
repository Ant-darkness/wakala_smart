from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_type: str
    title: str
    body: str
    payload: dict[str, Any] | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationFeedResponse(BaseModel):
    items: list[NotificationResponse]
    total: int = Field(ge=0)
    unread_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class NotificationReadResponse(BaseModel):
    id: UUID
    is_read: bool
    read_at: datetime | None


class NotificationReadAllResponse(BaseModel):
    updated_count: int = Field(ge=0)
