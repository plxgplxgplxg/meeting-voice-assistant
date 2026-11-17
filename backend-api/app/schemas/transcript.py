import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegmentUpdate(BaseModel):
    """Schema for updating an individual transcript segment."""
    content: str | None = Field(default=None, min_length=1)
    speaker_label: str | None = Field(default=None, min_length=1, max_length=100)


class BulkRenameSpeakerRequest(BaseModel):
    """Schema for updating a speaker's name across all segments in a meeting."""
    old_speaker_label: str = Field(min_length=1, max_length=100)
    new_speaker_label: str = Field(min_length=1, max_length=100)


class DeleteSegmentsRequest(BaseModel):
    """Schema for deleting multiple transcript segments."""
    segment_ids: list[uuid.UUID] = Field(min_length=1)


class TranscriptSegmentResponse(BaseModel):
    """Schema representing an individual chronological transcript turn."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    speaker_label: str
    start_time: float
    end_time: float
    content: str
    sequence_order: int
    version: int = 1
    created_at: datetime
