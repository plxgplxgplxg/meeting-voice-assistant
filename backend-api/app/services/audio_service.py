import os
import uuid
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger(__name__)

from app.models.audio_file import AudioFileModel
from app.models.meeting import MeetingModel
from app.models.user import UserModel
from app.schemas.audio import AudioPlaybackResponse, AudioUploadResponse
from app.services.storage_service import StorageService

ALLOWED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".webm",
    ".mp4",
}


class AudioService:
    """Service handling audio file ingestion, validation, and playback resolution."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.storage_service = StorageService()

    async def handle_uploaded_audio(
        self,
        file: UploadFile,
        title: str | None,
        user: UserModel | None,
        meeting_id: uuid.UUID | None = None,
    ) -> AudioUploadResponse:
        """Validate, store, and enqueue processing for an uploaded meeting recording.

        Args:
            file: The uploaded multipart audio file.
            title: Optional custom meeting title.
            user: Authenticated user uploading the file.
            meeting_id: Optional existing meeting UUID to append file to.

        Returns:
            AudioUploadResponse with meeting and audio file IDs.

        Raises:
            HTTPException: If file type is unsupported or upload fails.
        """
        filename = file.filename or "recording.wav"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio extension '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
            )

        # Create or fetch meeting
        if meeting_id:
            meeting = await self.session.get(MeetingModel, meeting_id)
            if not meeting:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found."
                )
        else:
            meeting_title = title or os.path.splitext(filename)[0].replace("_", " ").title()
            meeting = MeetingModel(
                title=meeting_title,
                status="processing",
                created_by=user.id if user else None,
            )
            self.session.add(meeting)
            await self.session.flush()

        # Save audio file
        storage_path, file_size = await self.storage_service.save_upload_file(
            meeting.id, file
        )

        audio_file = AudioFileModel(
            meeting_id=meeting.id,
            file_name=filename,
            storage_path=storage_path,
            mime_type=file.content_type or "audio/wav",
            duration_seconds=0.0,
            file_size_bytes=file_size,
            upload_status="completed",
        )
        self.session.add(audio_file)
        await self.session.flush()

        # Trigger background processing task via Celery with in-process async fallback
        task_dispatched = False
        try:
            from app.workers.celery_worker import celery_app

            celery_app.send_task(
                "process_audio_task", args=[str(meeting.id), storage_path]
            )
            task_dispatched = True
        except Exception as exc:
            logger.warning("celery_send_task_failed", error=str(exc))

        if not task_dispatched:
            try:
                import asyncio
                from app.workers.celery_worker import _async_process_audio

                asyncio.create_task(_async_process_audio(str(meeting.id), storage_path))
                logger.info("audio_task_enqueued_in_process_fallback", meeting_id=str(meeting.id))
            except Exception as exc:
                logger.error("audio_task_fallback_failed", error=str(exc))

        return AudioUploadResponse(
            meeting_id=meeting.id,
            audio_file_id=audio_file.id,
            file_name=audio_file.file_name,
            file_size_bytes=audio_file.file_size_bytes,
            status=meeting.status,
        )

    async def get_playback_info(
        self, meeting_id: uuid.UUID
    ) -> AudioPlaybackResponse:
        """Resolve streaming playback info for a meeting's primary audio file."""
        result = await self.session.execute(
            select(AudioFileModel)
            .where(AudioFileModel.meeting_id == meeting_id)
            .order_by(AudioFileModel.created_at.desc())
        )
        audio_file = result.scalars().first()

        if not audio_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No audio recording found for this meeting.",
            )

        return AudioPlaybackResponse(
            meeting_id=meeting_id,
            audio_file_id=audio_file.id,
            stream_url=f"/api/v1/audio/{meeting_id}/stream",
            mime_type=audio_file.mime_type,
            duration_seconds=audio_file.duration_seconds,
        )
