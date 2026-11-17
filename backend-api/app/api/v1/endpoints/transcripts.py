import uuid

from fastapi import APIRouter

from app.api.deps import (
    AccessPolicy,
    ActorDep,
    MeetingForEdit,
    MeetingForView,
    TranscriptEditorDep,
    TranscriptServiceDep,
)
from app.core.errors import ValidationFailedError
from app.domain.enums import Permission
from app.schemas.transcript import (
    BulkRenameSpeakerRequest,
    DeleteSegmentsRequest,
    TranscriptSegmentResponse,
    TranscriptSegmentUpdate,
)
from app.schemas.transcript_ops import (
    ChangeSetDetailResponse,
    ChangeSetResultResponse,
    ChangeSetSummaryResponse,
    DeleteSegments,
    OperationsPreviewRequest,
    OperationsRequest,
    ReassignSpeaker,
    RenameSpeaker,
    SegmentDiffResponse,
    TranscriptDiffResponse,
    UpdateText,
)

router = APIRouter(tags=["Transcripts"])
legacy_router = APIRouter(
    prefix="/transcripts", tags=["Transcripts (deprecated paths)"], deprecated=True
)


async def update_one_segment(
    editor: TranscriptEditorDep,
    service: TranscriptServiceDep,
    actor: ActorDep,
    meeting_id: uuid.UUID,
    segment_id: uuid.UUID,
    payload: TranscriptSegmentUpdate,
) -> TranscriptSegmentResponse:
    """Apply a single-segment edit through the editor and return the stored segment."""
    await service.get_segment(meeting_id, segment_id)
    operations = []
    if payload.content is not None:
        operations.append(UpdateText(segment_id=segment_id, new_text=payload.content))
    if payload.speaker_label is not None:
        operations.append(ReassignSpeaker(segment_ids=[segment_id], new_label=payload.speaker_label))
    if operations:
        try:
            await editor.apply(actor, meeting_id, operations, expected_revision=None)
        except ValidationFailedError as exc:
            if exc.code != "NO_CHANGES":
                raise
    segment = await service.get_segment(meeting_id, segment_id)
    return TranscriptSegmentResponse.model_validate(segment)


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
    actor: ActorDep,
    editor: TranscriptEditorDep,
    service: TranscriptServiceDep,
) -> TranscriptSegmentResponse:
    """Update text or speaker of a transcript segment."""
    return await update_one_segment(editor, service, actor, meeting.id, segment_id, payload)


@legacy_router.patch("/segments/{segment_id}", response_model=TranscriptSegmentResponse)
async def update_segment_legacy(
    segment_id: uuid.UUID,
    payload: TranscriptSegmentUpdate,
    actor: ActorDep,
    policy: AccessPolicy,
    editor: TranscriptEditorDep,
    service: TranscriptServiceDep,
) -> TranscriptSegmentResponse:
    """Deprecated: update a segment without the meeting id in the path."""
    meeting_id = await service.get_segment_meeting_id(segment_id)
    meeting = await policy.require(actor, meeting_id, Permission.EDIT)
    return await update_one_segment(editor, service, actor, meeting.id, segment_id, payload)


@router.post("/meetings/{meeting_id}/transcript/rename-speaker")
@legacy_router.post("/{meeting_id}/rename-speaker")
async def bulk_rename_speaker(
    payload: BulkRenameSpeakerRequest,
    meeting: MeetingForEdit,
    actor: ActorDep,
    editor: TranscriptEditorDep,
) -> dict[str, int | str]:
    """Rename a speaker across all segments in this meeting."""
    operation = RenameSpeaker(old_label=payload.old_speaker_label, new_label=payload.new_speaker_label)
    try:
        result = await editor.apply(actor, meeting.id, [operation], expected_revision=None)
        affected = len(result.affected_segment_ids)
    except ValidationFailedError as exc:
        if exc.code != "NO_CHANGES":
            raise
        affected = 0
    return {"affected_segments": affected, "new_speaker_label": payload.new_speaker_label}


@router.post("/meetings/{meeting_id}/transcript/delete-segments")
@legacy_router.post("/{meeting_id}/delete-segments")
async def delete_segments(
    payload: DeleteSegmentsRequest,
    meeting: MeetingForEdit,
    actor: ActorDep,
    editor: TranscriptEditorDep,
) -> dict[str, int]:
    """Delete multiple transcript segments."""
    result = await editor.apply(
        actor, meeting.id, [DeleteSegments(segment_ids=payload.segment_ids)], expected_revision=None
    )
    return {"deleted_segments": len(result.affected_segment_ids)}


@router.post(
    "/meetings/{meeting_id}/transcript/operations", response_model=ChangeSetResultResponse
)
async def apply_operations(
    payload: OperationsRequest,
    meeting: MeetingForEdit,
    actor: ActorDep,
    editor: TranscriptEditorDep,
) -> ChangeSetResultResponse:
    """Apply a batch of operations as one change set, optionally guarded by a revision."""
    result = await editor.apply(
        actor, meeting.id, payload.operations, payload.expected_revision, payload.reason
    )
    return result.to_response()


@router.post(
    "/meetings/{meeting_id}/transcript/operations:preview", response_model=TranscriptDiffResponse
)
async def preview_operations(
    payload: OperationsPreviewRequest,
    meeting: MeetingForEdit,
    actor: ActorDep,
    editor: TranscriptEditorDep,
) -> TranscriptDiffResponse:
    """Show what a batch of operations would change without writing anything."""
    return (await editor.preview(actor, meeting.id, payload.operations)).to_response()


@router.get(
    "/meetings/{meeting_id}/transcript/change-sets", response_model=list[ChangeSetSummaryResponse]
)
async def list_change_sets(
    meeting: MeetingForView, actor: ActorDep, editor: TranscriptEditorDep
) -> list[ChangeSetSummaryResponse]:
    """List the transcript edit history, newest first."""
    entries = await editor.list_change_sets(actor, meeting.id)
    return [
        ChangeSetSummaryResponse(
            id=cs.id,
            revision=cs.revision,
            actor_type=cs.actor_type,
            actor_user_id=cs.actor_user_id,
            summary=cs.summary,
            reverts_change_set_id=cs.reverts_change_set_id,
            reverted=reverted,
            created_at=cs.created_at,
        )
        for cs, reverted in entries
    ]


@router.get(
    "/meetings/{meeting_id}/transcript/change-sets/{change_set_id}",
    response_model=ChangeSetDetailResponse,
)
async def get_change_set(
    change_set_id: uuid.UUID, meeting: MeetingForView, actor: ActorDep, editor: TranscriptEditorDep
) -> ChangeSetDetailResponse:
    """Show one change set with the before and after of every segment it touched."""
    cs, reverted = await editor.get_change_set(actor, meeting.id, change_set_id)
    return ChangeSetDetailResponse(
        id=cs.id,
        revision=cs.revision,
        actor_type=cs.actor_type,
        actor_user_id=cs.actor_user_id,
        summary=cs.summary,
        reverts_change_set_id=cs.reverts_change_set_id,
        reverted=reverted,
        created_at=cs.created_at,
        operations=cs.operations,
        changes=[
            SegmentDiffResponse(op=c.op, segment_id=c.segment_id, before=c.before, after=c.after)
            for c in cs.changes
        ],
    )


@router.post(
    "/meetings/{meeting_id}/transcript/change-sets/{change_set_id}/revert",
    response_model=ChangeSetResultResponse,
)
async def revert_change_set(
    change_set_id: uuid.UUID, meeting: MeetingForEdit, actor: ActorDep, editor: TranscriptEditorDep
) -> ChangeSetResultResponse:
    """Undo a change set by applying its inverse as a new change set."""
    return (await editor.revert(actor, meeting.id, change_set_id)).to_response()
