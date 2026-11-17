import re
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field

from app.core.auth import require_service_token
from app.deps import AudioProcessor, resolve_storage_key

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/audio", tags=["Audio Pipeline"], dependencies=[Depends(require_service_token)]
)

PROVIDER_JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class TranscribeRequest(BaseModel):
    """Payload to start audio transcription and diarization."""

    meeting_id: str = Field(description="UUID string of the target meeting, for tracing")
    storage_key: str = Field(description="Recording key relative to the storage root")
    language: str = Field(default="vi", description="Primary spoken language code")
    min_speakers: int = Field(default=1, ge=1, le=20)
    max_speakers: int = Field(default=6, ge=1, le=20)


class TranscribeSubmitResponse(BaseModel):
    """Handle returned right after a job was started."""

    provider_job_id: str
    status: str = "submitted"


class TranscribeStatusResponse(BaseModel):
    """Current state of a transcription job."""

    status: str
    is_demo: bool = False
    segments_count: int = 0
    segments: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


@router.post("/transcribe", response_model=TranscribeSubmitResponse)
async def submit_transcription(
    payload: TranscribeRequest, processor: AudioProcessor
) -> TranscribeSubmitResponse:
    """Start transcribing a stored recording and return a job id without waiting.

    The storage key is resolved strictly inside ``STORAGE_ROOT``; arbitrary
    filesystem paths and URLs are rejected.
    """
    audio_path = resolve_storage_key(payload.storage_key)
    logger.info("transcribe_submit", meeting_id=payload.meeting_id, storage_key=payload.storage_key)
    provider_job_id = await processor.submit(
        audio_path=str(audio_path),
        language=payload.language,
        min_speakers=payload.min_speakers,
        max_speakers=payload.max_speakers,
    )
    return TranscribeSubmitResponse(provider_job_id=provider_job_id)


@router.get("/transcribe/{provider_job_id}", response_model=TranscribeStatusResponse)
async def get_transcription(
    provider_job_id: Annotated[str, Path(pattern=PROVIDER_JOB_ID_PATTERN.pattern)],
    processor: AudioProcessor,
) -> TranscribeStatusResponse:
    """Check a transcription job once. Returns segments when the job is done."""
    result = await processor.get_result(provider_job_id)
    return TranscribeStatusResponse(
        status=result.status,
        is_demo=bool(getattr(processor, "is_demo", False)),
        segments_count=len(result.segments),
        segments=result.segments,
        error=result.error,
    )
