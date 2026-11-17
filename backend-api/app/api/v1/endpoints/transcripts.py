import uuid

from fastapi import APIRouter

from app.api.deps import (
    AccessPolicy,
    ActorDep,
    MeetingForEdit,
    MeetingForView,
    TranscriptServiceDep,
)
from app.domain.enums import Permission
from app.schemas.transcript import (
    BulkRenameSpeakerRequest,
    DeleteSegmentsRequest,
    TranscriptSegmentResponse,
    TranscriptSegmentUpdate,
)

router = APIRouter(tags=["Transcripts"])
legacy_router = APIRouter(
    prefix="/transcripts", tags=["Transcripts (deprecated paths)"], deprecated=True
)


@router.get("/meetings/{meeting_id}/transcript", response_model=list[TranscriptSegmentResponse])
@legacy_router.get("/{meeting_id}", response_model=list[TranscriptSegmentResponse])
async def get_segments(
    meeting: MeetingForView, service: TranscriptServiceDep
) -> list[TranscriptSegmentResponse]:
    """List chronological transcript segments for a meeting."""
    segments = await service.get_segments_by_meeting(meeting.id)
    return [TranscriptSegmentResponse.model_validate(s) for s in segments]


@router.patch(
    "/meetings/{meeting_id}/transcript/segments/{segment_id}",
    response_model=TranscriptSegmentResponse,
)
async def update_segment(
    segment_id: uuid.UUID,
    payload: TranscriptSegmentUpdate,
    meeting: MeetingForEdit,
    service: TranscriptServiceDep,
) -> TranscriptSegmentResponse:
    """Update text or speaker of a transcript segment."""
    segment = await service.update_segment(meeting.id, segment_id, payload)
    return TranscriptSegmentResponse.model_validate(segment)


@legacy_router.patch("/segments/{segment_id}", response_model=TranscriptSegmentResponse)
async def update_segment_legacy(
    segment_id: uuid.UUID,
    payload: TranscriptSegmentUpdate,
    actor: ActorDep,
    policy: AccessPolicy,
    service: TranscriptServiceDep,
) -> TranscriptSegmentResponse:
    """Deprecated: update a segment without the meeting id in the path."""
    meeting_id = await service.get_segment_meeting_id(segment_id)
    meeting = await policy.require(actor, meeting_id, Permission.EDIT)
    segment = await service.update_segment(meeting.id, segment_id, payload)
    return TranscriptSegmentResponse.model_validate(segment)


@router.post("/meetings/{meeting_id}/transcript/rename-speaker")
@legacy_router.post("/{meeting_id}/rename-speaker")
async def bulk_rename_speaker(
    payload: BulkRenameSpeakerRequest,
    meeting: MeetingForEdit,
    service: TranscriptServiceDep,
) -> dict[str, int | str]:
    """Rename a speaker across all segments in this meeting."""
    affected = await service.bulk_rename_speaker(
        meeting.id, payload.old_speaker_label, payload.new_speaker_label
    )
    return {"affected_segments": affected, "new_speaker_label": payload.new_speaker_label}


@router.post("/meetings/{meeting_id}/transcript/delete-segments")
@legacy_router.post("/{meeting_id}/delete-segments")
async def delete_segments(
    payload: DeleteSegmentsRequest,
    meeting: MeetingForEdit,
    service: TranscriptServiceDep,
) -> dict[str, int]:
    """Delete multiple transcript segments."""
    deleted = await service.delete_segments(meeting.id, payload.segment_ids)
    return {"deleted_segments": deleted}
