from fastapi import APIRouter, status

from app.api.deps import MeetingForEdit, ProcessingCommandsDep

router = APIRouter(tags=["Processing"])


@router.post("/meetings/{meeting_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_meeting(
    meeting: MeetingForEdit, commands: ProcessingCommandsDep
) -> dict[str, str]:
    """Queue a rebuild of the retrieval index used for question answering."""
    await commands.request_reindex(meeting)
    return {"index_status": meeting.index_status}


@router.post("/meetings/{meeting_id}/summary:regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_summary(
    meeting: MeetingForEdit, commands: ProcessingCommandsDep
) -> dict[str, str]:
    """Queue a new summary and action items from the current (possibly edited) transcript."""
    await commands.request_summary_regeneration(meeting)
    return {"summary_status": meeting.summary_status}
