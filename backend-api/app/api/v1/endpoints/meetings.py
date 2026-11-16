import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user, get_current_user_optional
from app.models.user import UserModel
from app.schemas.meeting import (
    MeetingCreate,
    MeetingResponse,
    MeetingShareLinkResponse,
    MeetingUpdate,
)
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/meetings", tags=["Meetings"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
OptionalUser = Annotated[UserModel | None, Depends(get_current_user_optional)]
CurrentUser = Annotated[UserModel, Depends(get_current_user)]


@router.get("", response_model=list[MeetingResponse])
async def list_meetings(
    db: DatabaseSession,
    current_user: OptionalUser = None,
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[MeetingResponse]:
    """List accessible meetings with search and status filtering."""
    service = MeetingService(db)
    meetings = await service.list_meetings(
        user=current_user,
        search=search,
        status_filter=status_filter,
    )
    return [MeetingResponse.model_validate(m) for m in meetings]


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate,
    db: DatabaseSession,
    current_user: OptionalUser = None,
) -> MeetingResponse:
    """Create a new meeting session."""
    service = MeetingService(db)
    meeting = await service.create_meeting(payload, user=current_user)
    return MeetingResponse.model_validate(meeting)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: uuid.UUID,
    db: DatabaseSession,
    current_user: OptionalUser = None,
    share_token: str | None = Query(default=None, alias="share"),
) -> MeetingResponse:
    """Retrieve specific meeting details verifying user or share token access."""
    service = MeetingService(db)
    meeting = await service.verify_meeting_access(
        meeting_id=meeting_id,
        user=current_user,
        share_token=share_token,
        required_permission="viewer",
    )
    return MeetingResponse.model_validate(meeting)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: uuid.UUID,
    payload: MeetingUpdate,
    db: DatabaseSession,
    current_user: OptionalUser = None,
    share_token: str | None = Query(default=None, alias="share"),
) -> MeetingResponse:
    """Update meeting details (Title, Status) requiring editor access."""
    service = MeetingService(db)
    meeting = await service.verify_meeting_access(
        meeting_id=meeting_id,
        user=current_user,
        share_token=share_token,
        required_permission="editor",
    )
    updated = await service.update_meeting(meeting, payload)
    return MeetingResponse.model_validate(updated)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: uuid.UUID,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> None:
    """Soft delete a meeting (Creator only)."""
    service = MeetingService(db)
    await service.soft_delete_meeting(meeting_id, current_user)


@router.post("/{meeting_id}/share", response_model=MeetingShareLinkResponse)
async def create_share_link(
    meeting_id: uuid.UUID,
    current_user: CurrentUser,
    db: DatabaseSession,
    permission: str = Query(default="viewer", pattern="^(viewer|editor)$"),
) -> MeetingShareLinkResponse:
    """Create or update a shareable link token for a meeting (Creator only)."""
    service = MeetingService(db)
    return await service.generate_share_link(meeting_id, permission, current_user)


@router.get("/{meeting_id}/export")
async def export_meeting(
    meeting_id: uuid.UUID,
    db: DatabaseSession,
    export_type: str = Query(default="txt", alias="type"),
) -> Response:
    """Export meeting transcript and summary in DOCX, TXT, SRT, VTT, or JSON format.

    Args:
        meeting_id: Meeting unique identifier.
        db: Active database session.
        export_type: Format string.

    Returns:
        Streaming response with attachment disposition.
    """
    from app.services.export_service import ExportService
    service = ExportService(db)
    body, content_type, extension = await service.export_meeting(meeting_id, export_type)
    filename = f"meeting_{str(meeting_id)[:8]}.{extension}"
    return Response(
        content=body,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
