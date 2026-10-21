import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MeetingBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class MeetingCreate(MeetingBase):
    pass


class MeetingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, max_length=50)


class MeetingResponse(MeetingBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    duration_seconds: float
    created_at: datetime
    updated_at: datetime
