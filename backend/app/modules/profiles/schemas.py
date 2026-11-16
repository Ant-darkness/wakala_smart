from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProfileSetupRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=150)
    phone: str = Field(min_length=9, max_length=20)
    tin: str | None = Field(default=None, max_length=30)
    nida: str | None = Field(default=None, max_length=30)
    profile_image_url: str | None = Field(default=None, max_length=500)


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=150)
    phone: str | None = Field(default=None, min_length=9, max_length=20)
    tin: str | None = Field(default=None, max_length=30)
    nida: str | None = Field(default=None, max_length=30)
    profile_image_url: str | None = Field(default=None, max_length=500)


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: EmailStr | None
    phone: str | None
    agent_number: str | None
    tin: str | None
    nida: str | None
    profile_image_url: str | None


class ProfileSetupResponse(BaseModel):
    profile: ProfileResponse
    security_token: str
    message: str
