import uuid

from pydantic import BaseModel, ConfigDict


class AudioUploadResponse(BaseModel):
    """Schema returned after an audio file is uploaded and queued."""
    model_config = ConfigDict(from_attributes=True)

    meeting_id: uuid.UUID
    audio_file_id: uuid.UUID
    file_name: str
    file_size_bytes: int
    status: str


class AudioPlaybackResponse(BaseModel):
    """Schema providing streaming playback URL and audio metadata."""
    meeting_id: uuid.UUID
    audio_file_id: uuid.UUID
    stream_url: str
    mime_type: str
    duration_seconds: float


class AudioStreamUrlResponse(BaseModel):
    """Short-lived signed URL for streaming a meeting recording in an audio element."""
    url: str
    expires_at: int
