import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MemberAddRequest(BaseModel):
    email: EmailStr
    role_code: str = Field(
        default="AGENT_OPERATOR",
        pattern=r"^AGENT_OPERATOR$",
    )


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    status: str
    joined_at: datetime | None
