from pydantic import BaseModel, Field


class PlatformAdminStatusRequest(BaseModel):
    is_active: bool
    reason: str = Field(min_length=10, max_length=500)


class PlatformAdminStatusResponse(BaseModel):
    message: str
    admin_id: str
    previous_status: bool
    current_status: bool
