import os
import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationFailedError
from app.core.security import sanitize_filename
from app.core.signed_urls import sign_audio_stream
from app.domain.enums import JobKind, MeetingStatus
from app.models.audio_file import AudioFileModel
from app.models.meeting import MeetingModel
from app.models.user import UserModel
from app.schemas.audio import AudioPlaybackResponse, AudioStreamUrlResponse, AudioUploadResponse
from app.services.audio_validation import ALLOWED_AUDIO_EXTENSIONS, looks_like_audio_container
from app.services.billing.quota_service import QuotaService
from app.services.processing.jobs import JobService
from app.services.processing.state import transition
from app.services.storage_service import StorageService


class AudioService:
    """Service handling audio ingestion, validation, and playback resolution."""

    def __init__(
        self,
        session: AsyncSession,
        storage: StorageService,
        quota_service: QuotaService,
        jobs: JobService,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            storage: Object storage for recordings.
            quota_service: Used to block uploads when the quota is exhausted.
            jobs: Queues background processing through the transactional outbox.
        """
        self.session = session
        self.storage = storage
        self.quota_service = quota_service
        self.jobs = jobs

    async def handle_uploaded_audio(
        self,
        file: UploadFile,
        title: str | None,
        user: UserModel,
        meeting: MeetingModel | None = None,
    ) -> AudioUploadResponse:
        """Validate, store, and enqueue processing for an uploaded recording.

        Args:
            file: The uploaded multipart audio file.
            title: Optional meeting title used when a meeting is created.
            user: Authenticated uploader.
            meeting: Existing meeting (already authorized for editing) to attach to.

        Returns:
            Meeting and audio file identifiers.

        Raises:
            ValidationFailedError: If the extension, size, or content is not acceptable.
            QuotaExceededError: If the user's quota is exhausted.
            InvalidStateError: If the meeting is currently being processed.
        """
        display_name = sanitize_filename(file.filename or "recording.wav")
        extension = os.path.splitext(display_name)[1].lower()
        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            raise ValidationFailedError(
                f"Unsupported audio extension '{extension}'. "
                f"Allowed formats: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
                code="UNSUPPORTED_AUDIO_TYPE",
                status_code=400,
            )

        await self.quota_service.assert_within_quota(user)

        if meeting is None:
            meeting_title = title or os.path.splitext(display_name)[0].replace("_", " ").title()
            meeting = MeetingModel(
                title=meeting_title, status=MeetingStatus.DRAFT, created_by=user.id
            )
            self.session.add(meeting)
            await self.session.flush()
        transition(meeting, MeetingStatus.UPLOADED)

        audio_file_id = uuid.uuid4()
        storage_key, size = await self.storage.save_upload(
            meeting.id, audio_file_id, extension, file
        )
        if not looks_like_audio_container(self.storage.read_head(storage_key)):
            self.storage.delete(storage_key)
            raise ValidationFailedError(
                "The uploaded file is not a valid audio or video recording.",
                code="INVALID_AUDIO_CONTENT",
                status_code=400,
            )

        audio_file = AudioFileModel(
            id=audio_file_id,
            meeting_id=meeting.id,
            file_name=display_name,
            storage_key=storage_key,
            mime_type=file.content_type or "audio/wav",
            duration_seconds=0.0,
            file_size_bytes=size,
            upload_status="completed",
        )
        self.session.add(audio_file)
        await self.session.flush()

        await self.jobs.enqueue(
            meeting.id, JobKind.TRANSCRIBE, f"transcribe:{audio_file.id}", audio_file.id
        )

        return AudioUploadResponse(
            meeting_id=meeting.id,
            audio_file_id=audio_file.id,
            file_name=audio_file.file_name,
            file_size_bytes=audio_file.file_size_bytes,
            status=meeting.status,
        )

    async def get_latest_audio(self, meeting_id: uuid.UUID) -> AudioFileModel:
        """Return the most recent audio file of a meeting.

        Raises:
            NotFoundError: If the meeting has no stored recording.
        """
        audio_file = await self.session.scalar(
            select(AudioFileModel)
            .where(AudioFileModel.meeting_id == meeting_id)
            .order_by(AudioFileModel.created_at.desc())
        )
        if audio_file is None or not self.storage.exists(audio_file.storage_key):
            raise NotFoundError("No audio recording found for this meeting.", code="AUDIO_NOT_FOUND")
        return audio_file

    async def reprocess(self, meeting: MeetingModel) -> AudioUploadResponse:
        """Re-run processing for the most recent recording of a meeting.

        Args:
            meeting: Meeting already authorized for editing.

        Returns:
            Identifiers of the meeting and the audio file being reprocessed.

        Raises:
            NotFoundError: If the meeting has no stored recording.
            InvalidStateError: If the meeting is currently being processed.
        """
        audio_file = await self.get_latest_audio(meeting.id)
        transition(meeting, MeetingStatus.UPLOADED)
        await self.session.flush()
        await self.jobs.enqueue(
            meeting.id,
            JobKind.TRANSCRIBE,
            f"transcribe:{audio_file.id}:{uuid.uuid4().hex}",
            audio_file.id,
        )
        return AudioUploadResponse(
            meeting_id=meeting.id,
            audio_file_id=audio_file.id,
            file_name=audio_file.file_name,
            file_size_bytes=audio_file.file_size_bytes,
            status=meeting.status,
        )

    async def get_stream_url(self, meeting_id: uuid.UUID) -> AudioStreamUrlResponse:
        """Issue a short-lived signed URL for streaming the latest recording.

        Raises:
            NotFoundError: If the meeting has no stored recording.
        """
        await self.get_latest_audio(meeting_id)
        expires_at, signature = sign_audio_stream(meeting_id)
        return AudioStreamUrlResponse(
            url=f"/api/v1/meetings/{meeting_id}/audio/stream?exp={expires_at}&sig={signature}",
            expires_at=expires_at,
        )

    async def get_playback_info(self, meeting_id: uuid.UUID) -> AudioPlaybackResponse:
        """Resolve streaming playback info for a meeting's primary audio file."""
        audio_file = await self.get_latest_audio(meeting_id)
        return AudioPlaybackResponse(
            meeting_id=meeting_id,
            audio_file_id=audio_file.id,
            stream_url=(await self.get_stream_url(meeting_id)).url,
            mime_type=audio_file.mime_type,
            duration_seconds=audio_file.duration_seconds,
        )
