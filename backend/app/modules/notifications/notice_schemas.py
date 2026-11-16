from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class NoticeCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    body: str = Field(min_length=1, max_length=10_000)
    starts_at: datetime
    ends_at: datetime | None = None
    is_published: bool = False

    @field_validator("title", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty.")

        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.starts_at.tzinfo is None or self.starts_at.utcoffset() is None:
            raise ValueError("starts_at must include a timezone.")

        if self.ends_at is not None:
            if self.ends_at.tzinfo is None or self.ends_at.utcoffset() is None:
                raise ValueError("ends_at must include a timezone.")

            if self.ends_at <= self.starts_at:
                raise ValueError("ends_at must be after starts_at.")

        return self


class NoticeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None
    title: str
    body: str
    is_published: bool
    starts_at: datetime
    ends_at: datetime | None
    created_at: datetime
