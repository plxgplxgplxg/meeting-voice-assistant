import uuid
from typing import Any

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_service_client import AIServiceClient
from app.core.errors import AIUnavailableError, DomainError
from app.domain.enums import MeetingStatus, SummaryStatus
from app.models.audio_file import AudioFileModel
from app.models.meeting import MeetingModel
from app.models.summary import ActionItemModel, SummaryModel
from app.models.transcript import TranscriptSegmentModel
from app.services.billing.quota_service import QuotaService
from app.services.processing.state import transition

logger = structlog.get_logger(__name__)

SOURCE_AI = "ai"


class MeetingProcessingPipeline:
    """Orchestrates ASR, summarization, and quota charging for one meeting.

    Collaborators are injected so the pipeline is unit-testable without Celery
    or a real AI service. Each run is safe to repeat: segments are replaced and
    the summary is upserted. The pipeline only flushes, the caller owns the
    transaction.
    """

    def __init__(
        self,
        session: AsyncSession,
        ai_client: AIServiceClient,
        quota_service: QuotaService,
    ) -> None:
        """Initialize the pipeline.

        Args:
            session: Active SQLAlchemy session.
            ai_client: Client for the AI service.
            quota_service: Charges usage after successful processing.
        """
        self.session = session
        self.ai_client = ai_client
        self.quota_service = quota_service

    async def run(self, meeting_id: uuid.UUID, audio_file_id: uuid.UUID) -> MeetingStatus:
        """Process an uploaded recording end to end.

        Failures are recorded on the meeting (``failed`` with stage and reason)
        instead of being papered over with placeholder data. Quota is charged
        only after the transcript was produced successfully.

        Args:
            meeting_id: Meeting being processed.
            audio_file_id: Uploaded audio file to transcribe.

        Returns:
            The final meeting status (``ready`` or ``failed``).

        Raises:
            DomainError: If the meeting or audio file does not exist.
        """
        meeting = await self.session.get(MeetingModel, meeting_id)
        audio = await self.session.get(AudioFileModel, audio_file_id)
        if meeting is None or audio is None or audio.meeting_id != meeting.id:
            raise DomainError("Meeting or audio file not found.", code="PROCESSING_TARGET_MISSING")

        transition(meeting, MeetingStatus.TRANSCRIBING)
        meeting.summary_status = SummaryStatus.NONE
        await self.session.flush()

        try:
            transcription = await self.ai_client.transcribe(str(meeting.id), audio.storage_key)
        except AIUnavailableError as exc:
            return await self._fail(meeting, "transcribe", exc.message)
        segments = transcription.segments
        if not segments:
            return await self._fail(meeting, "transcribe", "No speech was detected in the recording.")

        meeting.is_demo = transcription.is_demo

        await self._replace_segments(meeting.id, segments)
        meeting.duration_seconds = max(float(s.get("end", 0.0)) for s in segments)
        if audio.duration_seconds <= 0:
            audio.duration_seconds = meeting.duration_seconds

        transition(meeting, MeetingStatus.SUMMARIZING)
        meeting.summary_status = SummaryStatus.PENDING
        await self.session.flush()
        await self._summarize(meeting, segments)

        transition(meeting, MeetingStatus.READY)
        if meeting.created_by is not None:
            await self.quota_service.record_usage(
                user_id=meeting.created_by,
                meeting_id=meeting.id,
                duration_seconds=audio.duration_seconds,
                audio_file_id=audio.id,
            )
        await self.session.flush()
        return MeetingStatus.READY

    async def _summarize(self, meeting: MeetingModel, segments: list[dict[str, Any]]) -> None:
        """Generate the summary, recording a ``failed`` summary status on error."""
        transcript = "\n".join(
            f"{s.get('speaker', 'Speaker')}: {s.get('text', '')}" for s in segments
        )
        try:
            result = await self.ai_client.summarize(str(meeting.id), transcript)
        except AIUnavailableError as exc:
            logger.warning("summary_generation_failed", meeting_id=str(meeting.id), error=exc.message)
            meeting.summary_status = SummaryStatus.FAILED
            return

        summary = await self.session.scalar(
            select(SummaryModel).where(SummaryModel.meeting_id == meeting.id)
        )
        if summary is None:
            summary = SummaryModel(meeting_id=meeting.id, executive_summary="", key_points=[])
            self.session.add(summary)
        summary.executive_summary = str(result.get("executive_summary", ""))
        summary.key_points = list(result.get("key_points", []))

        await self.session.execute(
            delete(ActionItemModel).where(
                ActionItemModel.meeting_id == meeting.id, ActionItemModel.source == SOURCE_AI
            )
        )
        for item in result.get("action_items", []):
            self.session.add(
                ActionItemModel(
                    meeting_id=meeting.id,
                    description=str(item.get("description", "")).strip() or "Untitled task",
                    assignee=str(item.get("assignee") or "Unassigned"),
                    status="pending",
                    source=SOURCE_AI,
                )
            )
        meeting.summary_status = SummaryStatus.READY

    async def _replace_segments(
        self, meeting_id: uuid.UUID, segments: list[dict[str, Any]]
    ) -> None:
        """Replace all transcript segments of a meeting so reruns never duplicate rows."""
        await self.session.execute(
            delete(TranscriptSegmentModel).where(TranscriptSegmentModel.meeting_id == meeting_id)
        )
        for order, segment in enumerate(segments, start=1):
            self.session.add(
                TranscriptSegmentModel(
                    meeting_id=meeting_id,
                    speaker_label=str(segment.get("speaker", "Speaker 1")),
                    start_time=float(segment.get("start", 0.0)),
                    end_time=float(segment.get("end", 0.0)),
                    content=str(segment.get("text", "")),
                    sequence_order=order,
                )
            )
        await self.session.flush()

    async def _fail(self, meeting: MeetingModel, stage: str, reason: str) -> MeetingStatus:
        logger.warning(
            "meeting_processing_failed", meeting_id=str(meeting.id), stage=stage, reason=reason
        )
        transition(meeting, MeetingStatus.FAILED, failure_stage=stage, failure_reason=reason)
        await self.session.flush()
        return MeetingStatus.FAILED
