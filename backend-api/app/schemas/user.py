import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """Schema representing user profile details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime


class UserUpdateRequest(BaseModel):
    """Schema for updating basic user profile information."""
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=2048)


class ChangePasswordRequest(BaseModel):
    """Schema for changing a user's password."""
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)
