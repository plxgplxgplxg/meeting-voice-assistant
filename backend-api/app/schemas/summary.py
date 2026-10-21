import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class SummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    executive_summary: str
    key_points: list[Any]
    created_at: datetime


class ActionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    description: str
    assignee: str
    status: str
    due_date: datetime | None = None
    created_at: datetime
