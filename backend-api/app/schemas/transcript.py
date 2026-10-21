import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegmentUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    speaker_label: str | None = Field(default=None, min_length=1, max_length=100)


class TranscriptSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    speaker_label: str
    start_time: float
    end_time: float
    content: str
    sequence_order: int
    created_at: datetime
