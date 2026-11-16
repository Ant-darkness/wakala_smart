import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=9, max_length=20)
    password: str = Field(min_length=12, max_length=128)


class EmailVerifyRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str | None
    phone: str | None
    agent_number: str | None


class SecurityTokenVerifyRequest(BaseModel):
    security_token: str = Field(pattern=r"^\d{5}$")


class SecurityTokenResetRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_security_token: str = Field(pattern=r"^\d{5}$")


class AuthSessionResponse(BaseModel):
    id: uuid.UUID
    expires_at: datetime
