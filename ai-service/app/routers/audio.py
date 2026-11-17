from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import require_service_token
from app.deps import AudioProcessor, resolve_storage_key

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/audio", tags=["Audio Pipeline"], dependencies=[Depends(require_service_token)]
)


class TranscribeRequest(BaseModel):
    """Payload to request audio transcription and diarization."""

    meeting_id: str = Field(description="UUID string of the target meeting, for tracing")
    storage_key: str = Field(description="Recording key relative to the storage root")
    language: str = Field(default="vi", description="Primary spoken language code")
    min_speakers: int = Field(default=1, ge=1, le=20)
    max_speakers: int = Field(default=6, ge=1, le=20)


class TranscribeResponse(BaseModel):
    """Segments produced for one recording."""

    meeting_id: str
    status: str
    is_demo: bool = False
    segments_count: int
    segments: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(payload: TranscribeRequest, processor: AudioProcessor) -> TranscribeResponse:
    """Transcribe and diarize a stored recording.

    The storage key is resolved strictly inside ``STORAGE_ROOT``; arbitrary
    filesystem paths and URLs are rejected.
    """
    audio_path = resolve_storage_key(payload.storage_key)
    logger.info("transcribe_request", meeting_id=payload.meeting_id, storage_key=payload.storage_key)

    segments = await processor.process_audio(
        audio_path=str(audio_path),
        language=payload.language,
        min_speakers=payload.min_speakers,
        max_speakers=payload.max_speakers,
    )
    return TranscribeResponse(
        meeting_id=payload.meeting_id,
        status="completed",
        is_demo=bool(getattr(processor, "is_demo", False)),
        segments_count=len(segments),
        segments=segments,
    )
