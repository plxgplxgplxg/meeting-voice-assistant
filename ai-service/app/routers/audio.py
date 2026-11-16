from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import structlog

from app.pipelines.gladia import GladiaAudioPipeline

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/audio", tags=["Audio Pipeline"])


class ProcessAudioRequest(BaseModel):
    """Payload to request audio transcription and diarization processing."""
    meeting_id: str = Field(description="UUID string of target meeting")
    audio_path: str = Field(description="Local or container filesystem path to audio recording")
    language: str = Field(default="vi", description="Primary spoken language code")


class TranscriptSegmentOutput(BaseModel):
    """Segment representation returned to backend caller."""
    speaker: str
    start: float
    end: float
    text: str
    words: list[dict[str, Any]] = []


class ProcessAudioResponse(BaseModel):
    """Response containing status, segment counts, and structured segments."""
    meeting_id: str
    status: str
    segments_count: int
    segments: list[dict[str, Any]] = []


@router.post("/process", response_model=ProcessAudioResponse)
async def process_audio(payload: ProcessAudioRequest) -> ProcessAudioResponse:
    """Execute ASR and diarization pipeline on uploaded audio via Gladia API."""
    logger.info("processing_audio_request", meeting_id=payload.meeting_id, audio_path=payload.audio_path)
    pipeline = GladiaAudioPipeline()

    try:
        segments = await pipeline.process_audio(
            audio_path=payload.audio_path,
            language=payload.language,
        )
    except FileNotFoundError as exc:
        logger.error("audio_file_not_found", path=payload.audio_path)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.exception("audio_processing_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio processing failed: {str(exc)}",
        )

    return ProcessAudioResponse(
        meeting_id=payload.meeting_id,
        status="completed",
        segments_count=len(segments),
        segments=segments,
    )
