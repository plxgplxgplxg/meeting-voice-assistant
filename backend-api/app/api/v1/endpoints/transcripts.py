import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.transcript import (
    BulkRenameSpeakerRequest,
    DeleteSegmentsRequest,
    TranscriptSegmentResponse,
    TranscriptSegmentUpdate,
)
from app.services.transcript_service import TranscriptService

router = APIRouter(prefix="/transcripts", tags=["Transcripts"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/{meeting_id}", response_model=list[TranscriptSegmentResponse])
async def get_segments(
    meeting_id: uuid.UUID, db: DatabaseSession
) -> list[TranscriptSegmentResponse]:
    """List chronological transcript segments for a meeting."""
    service = TranscriptService(db)
    segments = await service.get_segments_by_meeting(meeting_id)
    return [TranscriptSegmentResponse.model_validate(s) for s in segments]


@router.patch("/segments/{segment_id}", response_model=TranscriptSegmentResponse)
async def update_segment(
    segment_id: uuid.UUID,
    payload: TranscriptSegmentUpdate,
    db: DatabaseSession,
) -> TranscriptSegmentResponse:
    """Update text or speaker of a specific transcript segment."""
    service = TranscriptService(db)
    segment = await service.update_segment(segment_id, payload)
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript segment with ID '{segment_id}' not found.",
        )
    return TranscriptSegmentResponse.model_validate(segment)


@router.post("/{meeting_id}/rename-speaker")
async def bulk_rename_speaker(
    meeting_id: uuid.UUID,
    payload: BulkRenameSpeakerRequest,
    db: DatabaseSession,
) -> dict[str, int | str]:
    """Rename a speaker across all segments in this meeting."""
    service = TranscriptService(db)
    affected = await service.bulk_rename_speaker(
        meeting_id, payload.old_speaker_label, payload.new_speaker_label
    )
    return {
        "affected_segments": affected,
        "new_speaker_label": payload.new_speaker_label,
    }


@router.post("/{meeting_id}/delete-segments")
async def delete_segments(
    meeting_id: uuid.UUID,
    payload: DeleteSegmentsRequest,
    db: DatabaseSession,
) -> dict[str, int]:
    """Delete multiple transcript segments."""
    service = TranscriptService(db)
    deleted = await service.delete_segments(meeting_id, payload.segment_ids)
    return {"deleted_segments": deleted}
