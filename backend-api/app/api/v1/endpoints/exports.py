import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["Exports"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/{meeting_id}/{format}")
async def export_meeting_document(
    meeting_id: uuid.UUID,
    format: str,
    db: DatabaseSession,
) -> Response:
    """Export meeting transcript and summary in DOCX, TXT, SRT, VTT, or JSON format."""
    service = ExportService(db)
    body, content_type, extension = await service.export_meeting(meeting_id, format)

    filename = f"meeting_{str(meeting_id)[:8]}.{extension}"
    return Response(
        content=body,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
