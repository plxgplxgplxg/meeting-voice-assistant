import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MeetingBase(BaseModel):
    """Base schema for meeting properties."""
    title: str = Field(min_length=1, max_length=255)


class MeetingCreate(MeetingBase):
    """Schema for initializing a new meeting."""
    pass


class MeetingUpdate(BaseModel):
    """Schema for updating meeting attributes."""
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, max_length=50)


class MeetingResponse(MeetingBase):
    """Schema representing meeting session details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    duration_seconds: float
    created_by: uuid.UUID | None = None
    share_token: str | None = None
    share_permission: str = "viewer"
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime


class MeetingShareLinkResponse(BaseModel):
    """Schema returning a public or restricted shareable link."""
    meeting_id: uuid.UUID
    share_token: str
    share_url: str
    share_permission: str
