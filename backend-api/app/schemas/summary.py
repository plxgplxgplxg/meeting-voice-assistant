import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SummaryResponse(BaseModel):
    """Schema representing AI meeting summary."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    executive_summary: str
    key_points: list[Any]
    created_at: datetime


class ActionItemUpdate(BaseModel):
    """Schema for updating an action item status or assignee."""
    status: str | None = Field(default=None, pattern="^(pending|completed)$")
    assignee: str | None = None
    description: str | None = None


class ActionItemResponse(BaseModel):
    """Schema representing an action item checklist task."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    description: str
    assignee: str
    status: str
    due_date: datetime | None = None
    created_at: datetime
