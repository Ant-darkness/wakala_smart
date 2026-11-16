import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class InvitationCreateRequest(BaseModel):
    email: EmailStr


class InvitationAcceptRequest(BaseModel):
    token: str


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    invited_user_id: uuid.UUID
    role_id: uuid.UUID
    status: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
