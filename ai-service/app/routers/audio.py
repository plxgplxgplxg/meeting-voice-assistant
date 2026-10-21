from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/audio", tags=["Audio Pipeline"])


class ProcessAudioRequest(BaseModel):
    meeting_id: str
    audio_path: str


class ProcessAudioResponse(BaseModel):
    meeting_id: str
    status: str
    segments_count: int


@router.post("/process", response_model=ProcessAudioResponse)
async def process_audio(payload: ProcessAudioRequest) -> ProcessAudioResponse:
    """Execute ASR and diarization pipeline on uploaded audio."""
    return ProcessAudioResponse(
        meeting_id=payload.meeting_id,
        status="completed",
        segments_count=0,
    )
