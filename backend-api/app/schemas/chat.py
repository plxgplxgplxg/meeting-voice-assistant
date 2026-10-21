import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ChatQueryRequest(BaseModel):
    query: str = Field(min_length=1)


class Citation(BaseModel):
    segment_id: str
    speaker_label: str
    start_time: float
    end_time: float
    quote: str


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    citations: list[dict[str, Any]]
    created_at: datetime
