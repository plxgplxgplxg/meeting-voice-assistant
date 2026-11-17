from fastapi import APIRouter, Response

from app.api.deps import ExportServiceDep, MeetingForView

router = APIRouter(tags=["Exports"])
legacy_router = APIRouter(prefix="/exports", tags=["Exports (deprecated paths)"], deprecated=True)


@router.get("/meetings/{meeting_id}/exports/{format}")
@legacy_router.get("/{meeting_id}/{format}")
async def export_meeting_document(
    format: str, meeting: MeetingForView, service: ExportServiceDep
) -> Response:
    """Export meeting transcript and summary in DOCX, TXT, SRT, VTT, or JSON format."""
    body, content_type, extension = await service.export_meeting(meeting, format)
    filename = f"meeting_{str(meeting.id)[:8]}.{extension}"
    return Response(
        content=body,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
