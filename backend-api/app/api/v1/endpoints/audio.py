import os
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user_optional
from app.models.audio_file import AudioFileModel
from app.models.user import UserModel
from app.schemas.audio import AudioPlaybackResponse, AudioUploadResponse
from app.services.audio_service import AudioService

router = APIRouter(prefix="/audio", tags=["Audio"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
OptionalUser = Annotated[UserModel | None, Depends(get_current_user_optional)]


@router.post("/upload", response_model=AudioUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    db: DatabaseSession,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    meeting_id: uuid.UUID | None = Form(default=None),
    current_user: OptionalUser = None,
) -> AudioUploadResponse:
    """Upload a meeting audio or video recording file for processing.

    Args:
        db: Active asynchronous database session.
        file: Multipart audio file payload.
        title: Optional custom meeting title.
        meeting_id: Optional existing meeting UUID.
        current_user: Authenticated user uploading the file.

    Returns:
        AudioUploadResponse containing meeting and audio file metadata.
    """
    service = AudioService(db)
    return await service.handle_uploaded_audio(
        file=file,
        title=title,
        user=current_user,
        meeting_id=meeting_id,
    )


@router.post("/meetings/{meeting_id}/upload", response_model=AudioUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_meeting_audio_file(
    meeting_id: uuid.UUID,
    db: DatabaseSession,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    current_user: OptionalUser = None,
) -> AudioUploadResponse:
    """Upload an audio recording attached directly to a specific meeting.

    Args:
        meeting_id: Target meeting UUID.
        db: Active asynchronous database session.
        file: Multipart audio file payload.
        title: Optional custom meeting title override.
        current_user: Authenticated user uploading the file.

    Returns:
        AudioUploadResponse containing meeting and audio file metadata.
    """
    service = AudioService(db)
    return await service.handle_uploaded_audio(
        file=file,
        title=title,
        user=current_user,
        meeting_id=meeting_id,
    )


@router.get("/{meeting_id}/playback", response_model=AudioPlaybackResponse)
async def get_audio_playback(
    meeting_id: uuid.UUID, db: DatabaseSession
) -> AudioPlaybackResponse:
    """Get audio playback metadata and stream URL for a meeting."""
    service = AudioService(db)
    return await service.get_playback_info(meeting_id)


@router.get("/{meeting_id}/stream")
async def stream_meeting_audio(
    meeting_id: uuid.UUID, db: DatabaseSession
) -> FileResponse:
    """Stream audio file with HTTP Range support for timeline scrubbing."""
    result = await db.execute(
        select(AudioFileModel)
        .where(AudioFileModel.meeting_id == meeting_id)
        .order_by(AudioFileModel.created_at.desc())
    )
    audio_file = result.scalars().first()

    if not audio_file or not os.path.exists(audio_file.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found on disk.",
        )

    return FileResponse(
        path=audio_file.storage_path,
        media_type=audio_file.mime_type,
        filename=audio_file.file_name,
    )
