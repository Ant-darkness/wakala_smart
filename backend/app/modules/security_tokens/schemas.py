from pydantic import BaseModel, Field


class SecurityTokenVerifyRequest(BaseModel):
    token: str = Field(pattern=r"^\d{5}$")


class SecurityTokenResetRequest(BaseModel):
    current_password: str = Field(min_length=12)


class SecurityTokenResetResponse(BaseModel):
    security_token: str
    message: str


class SecurityTokenVerifyResponse(BaseModel):
    verified: bool
    message: str
