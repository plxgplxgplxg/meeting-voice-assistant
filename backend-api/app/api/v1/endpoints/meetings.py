import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.meeting import MeetingCreate, MeetingResponse, MeetingUpdate
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/meetings", tags=["Meetings"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=list[MeetingResponse])
async def list_meetings(db: DatabaseSession) -> list[MeetingResponse]:
    """List all meetings."""
    service = MeetingService(db)
    meetings = await service.list_meetings()
    return [MeetingResponse.model_validate(m) for m in meetings]


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(payload: MeetingCreate, db: DatabaseSession) -> MeetingResponse:
    """Create a new meeting."""
    service = MeetingService(db)
    meeting = await service.create_meeting(payload)
    return MeetingResponse.model_validate(meeting)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: uuid.UUID, db: DatabaseSession) -> MeetingResponse:
    """Retrieve specific meeting details."""
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID '{meeting_id}' not found.",
        )
    return MeetingResponse.model_validate(meeting)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: uuid.UUID, payload: MeetingUpdate, db: DatabaseSession
) -> MeetingResponse:
    """Update meeting details."""
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID '{meeting_id}' not found.",
        )
    updated = await service.update_meeting(meeting, payload)
    return MeetingResponse.model_validate(updated)
