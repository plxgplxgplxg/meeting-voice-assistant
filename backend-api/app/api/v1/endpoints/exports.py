import uuid
from fastapi import APIRouter, HTTPException, Response, status

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.get("/{meeting_id}/txt")
async def export_txt(meeting_id: uuid.UUID) -> Response:
    """Export meeting transcript in plain text format."""
    content = f"Meeting Transcript Export\nID: {meeting_id}\n"
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=meeting_{meeting_id}.txt"},
    )
