import uuid

from fastapi import APIRouter, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import (
    AccessPolicy,
    ActorDep,
    AudioServiceDep,
    CurrentUser,
    MeetingForEdit,
    MeetingForView,
    Storage,
)
from app.core.signed_urls import verify_audio_stream
from app.domain.enums import Permission
from app.schemas.audio import AudioPlaybackResponse, AudioStreamUrlResponse, AudioUploadResponse

router = APIRouter(tags=["Audio"])
legacy_router = APIRouter(prefix="/audio", tags=["Audio (deprecated paths)"], deprecated=True)


@router.post("/audio/upload", response_model=AudioUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    current_user: CurrentUser,
    actor: ActorDep,
    policy: AccessPolicy,
    service: AudioServiceDep,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    meeting_id: uuid.UUID | None = Form(default=None),
) -> AudioUploadResponse:
    """Upload a recording, creating a new meeting or attaching to an editable one."""
    meeting = await policy.require(actor, meeting_id, Permission.EDIT) if meeting_id else None
    return await service.handle_uploaded_audio(file=file, title=title, user=current_user, meeting=meeting)


@router.post(
    "/meetings/{meeting_id}/audio",
    response_model=AudioUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
@legacy_router.post(
    "/meetings/{meeting_id}/upload",
    response_model=AudioUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_meeting_audio_file(
    current_user: CurrentUser,
    meeting: MeetingForEdit,
    service: AudioServiceDep,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
) -> AudioUploadResponse:
    """Upload a recording attached to an existing meeting (requires edit access)."""
    return await service.handle_uploaded_audio(file=file, title=title, user=current_user, meeting=meeting)


@router.get("/meetings/{meeting_id}/audio/playback", response_model=AudioPlaybackResponse)
@legacy_router.get("/{meeting_id}/playback", response_model=AudioPlaybackResponse)
async def get_audio_playback(
    meeting: MeetingForView, service: AudioServiceDep
) -> AudioPlaybackResponse:
    """Get audio playback metadata and stream URL for a meeting."""
    return await service.get_playback_info(meeting.id)


@router.get("/meetings/{meeting_id}/audio/stream-url", response_model=AudioStreamUrlResponse)
async def get_audio_stream_url(
    meeting: MeetingForView, service: AudioServiceDep
) -> AudioStreamUrlResponse:
    """Issue a short-lived signed URL usable directly as an ``<audio>`` source."""
    return await service.get_stream_url(meeting.id)


@router.get("/meetings/{meeting_id}/audio/stream")
@legacy_router.get("/{meeting_id}/stream")
async def stream_meeting_audio(
    meeting_id: uuid.UUID,
    actor: ActorDep,
    policy: AccessPolicy,
    service: AudioServiceDep,
    storage: Storage,
    exp: int | None = Query(default=None),
    sig: str | None = Query(default=None),
) -> FileResponse:
    """Stream the audio file with HTTP Range support for timeline scrubbing.

    Access is granted either by a valid signed URL or by VIEW permission.
    """
    if exp is not None and sig is not None and verify_audio_stream(meeting_id, exp, sig):
        meeting = await policy.require_existing(meeting_id)
    else:
        meeting = await policy.require(actor, meeting_id, Permission.VIEW)
    audio_file = await service.get_latest_audio(meeting.id)
    return FileResponse(
        path=storage.resolve(audio_file.storage_key),
        media_type=audio_file.mime_type,
        filename=audio_file.file_name,
    )


@router.post("/meetings/{meeting_id}/reprocess", response_model=AudioUploadResponse)
async def reprocess_meeting(
    meeting: MeetingForEdit, service: AudioServiceDep
) -> AudioUploadResponse:
    """Re-run processing for the latest recording, e.g. after a failure."""
    return await service.reprocess(meeting)
