import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_service_client import AIServiceClient
from app.core.clock import utc_now
from app.core.errors import AIUnavailableError, DomainError, ValidationFailedError
from app.domain.enums import IndexStatus, JobKind, JobStatus, MeetingStatus, SummaryStatus
from app.domain.events import TranscriptReplaced
from app.models.audio_file import AudioFileModel
from app.models.meeting import MeetingModel
from app.models.processing_job import ProcessingJobModel
from app.models.summary import ActionItemModel, SummaryModel
from app.models.transcript import TranscriptSegmentModel
from app.services.audio_probe import AudioProbe
from app.services.billing.quota_service import QuotaService
from app.services.event_bus import EventBus
from app.services.processing.state import transition
from app.services.retrieval_service import TranscriptIndexer
from app.services.storage_service import StorageService

logger = structlog.get_logger(__name__)

SOURCE_AI = "ai"
TERMINAL_JOB_STATES = frozenset({JobStatus.SUCCEEDED, JobStatus.FAILED})


@dataclass(frozen=True, slots=True)
class PipelineSettings:
    """Timing and retry limits for background jobs."""

    poll_seconds: float = 5.0
    max_wait_seconds: float = 1800.0
    max_attempts: int = 3
    retry_base_seconds: float = 10.0


@dataclass(frozen=True, slots=True)
class StepOutcome:
    """Result of running one job step.

    Attributes:
        retry_in: Seconds to wait before running the same job again, or None when the job is over.
    """

    retry_in: float | None = None

    @property
    def done(self) -> bool:
        """Whether the job needs no further runs."""
        return self.retry_in is None


class MeetingProcessingPipeline:
    """Runs the transcribe, summarize, and index steps of meeting processing.

    Each step is one idempotent job: re-running it after a redelivery or crash is
    safe. Collaborators are injected so the pipeline is testable without Celery,
    an AI service, or ffprobe. The pipeline only flushes; the caller commits.
    """

    def __init__(
        self,
        session: AsyncSession,
        ai_client: AIServiceClient,
        quota_service: QuotaService,
        probe: AudioProbe,
        storage: StorageService,
        indexer: TranscriptIndexer,
        events: EventBus,
        settings: PipelineSettings | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        """Initialize the pipeline.

        Args:
            session: Active SQLAlchemy session.
            ai_client: Client for the AI service.
            quota_service: Charges usage once a meeting becomes ready.
            probe: Reads the real duration of recordings.
            storage: Resolves storage keys to files.
            indexer: Rebuilds the retrieval index.
            events: Publishes domain events; handlers queue the follow-up jobs.
            settings: Retry and polling limits.
            clock: Source of the current time, injectable for tests.
        """
        self.session = session
        self.ai_client = ai_client
        self.quota_service = quota_service
        self.probe = probe
        self.storage = storage
        self.indexer = indexer
        self.events = events
        self.settings = settings or PipelineSettings()
        self.clock = clock

    async def run_job(self, job_id: uuid.UUID) -> StepOutcome:
        """Run one processing job.

        The meeting row is locked for the duration so steps of one meeting never
        interleave, which is what lets summarize and index finish concurrently
        without both (or neither) completing the meeting.

        Args:
            job_id: Job to run.

        Returns:
            Whether the job finished or must be retried after a delay.

        Raises:
            DomainError: If the job or its meeting does not exist.
        """
        job = await self.session.get(ProcessingJobModel, job_id)
        if job is None:
            raise DomainError("Processing job not found.", code="JOB_NOT_FOUND")
        meeting = await self.session.scalar(
            select(MeetingModel).where(MeetingModel.id == job.meeting_id).with_for_update()
        )
        await self.session.refresh(job)
        if meeting is None:
            raise DomainError("Meeting not found.", code="PROCESSING_TARGET_MISSING")
        if job.status in TERMINAL_JOB_STATES:
            return StepOutcome()

        job.status = JobStatus.RUNNING
        job.started_at = job.started_at or self.clock()
        await self.session.flush()

        handlers = {
            JobKind.TRANSCRIBE: self._transcribe,
            JobKind.SUMMARIZE: self._summarize,
            JobKind.INDEX: self._index,
        }
        handler = handlers.get(JobKind(job.kind))
        if handler is None:
            raise DomainError(f"Unsupported job kind '{job.kind}'.", code="JOB_KIND_UNSUPPORTED")

        try:
            outcome = await handler(job, meeting)
        except AIUnavailableError as exc:
            outcome = await self._handle_ai_failure(job, meeting, exc)

        if outcome.done and job.status == JobStatus.RUNNING:
            job.status = JobStatus.SUCCEEDED
            job.finished_at = self.clock()
        await self.session.flush()
        return outcome

    async def _transcribe(self, job: ProcessingJobModel, meeting: MeetingModel) -> StepOutcome:
        audio = await self.session.get(AudioFileModel, job.audio_file_id)
        if audio is None or audio.meeting_id != meeting.id:
            return await self._fail_transcription(job, meeting, "probe", "Audio file not found.")

        if meeting.status == MeetingStatus.UPLOADED:
            transition(meeting, MeetingStatus.TRANSCRIBING)
            meeting.summary_status = SummaryStatus.NONE
            meeting.index_status = IndexStatus.NONE
        elif meeting.status != MeetingStatus.TRANSCRIBING:
            job.status = JobStatus.FAILED
            job.error = f"Meeting is '{meeting.status}', not awaiting transcription."
            job.finished_at = self.clock()
            return StepOutcome()

        if audio.duration_seconds <= 0:
            problem = await self._probe_audio(audio, meeting)
            if problem:
                return await self._fail_transcription(job, meeting, "probe", problem)

        if job.provider_job_id is None:
            job.provider_job_id = await self.ai_client.submit_transcription(
                str(meeting.id), audio.storage_key
            )
            return StepOutcome(retry_in=self.settings.poll_seconds)

        result = await self.ai_client.get_transcription(job.provider_job_id)
        if result.status == "processing":
            waited = (self.clock() - job.started_at).total_seconds()
            if waited > self.settings.max_wait_seconds:
                return await self._fail_transcription(
                    job, meeting, "transcribe", "Transcription timed out."
                )
            return StepOutcome(retry_in=self.settings.poll_seconds)
        if result.status == "error" or not result.segments:
            reason = result.error or "No speech was detected in the recording."
            return await self._fail_transcription(job, meeting, "transcribe", reason)

        await self._replace_segments(meeting, result.segments)
        meeting.is_demo = result.is_demo
        meeting.duration_seconds = audio.duration_seconds
        transition(meeting, MeetingStatus.SUMMARIZING)
        await self.events.publish(
            TranscriptReplaced(meeting.id, meeting.transcript_revision, audio.id)
        )
        return StepOutcome()

    async def _probe_audio(self, audio: AudioFileModel, meeting: MeetingModel) -> str | None:
        """Probe the recording, store its duration, and enforce the plan's length limit.

        Returns:
            A failure reason, or None when the audio is acceptable.
        """
        try:
            metadata = await self.probe.probe(self.storage.resolve(audio.storage_key))
        except ValidationFailedError as exc:
            return exc.message

        audio.duration_seconds = metadata.duration_seconds
        if meeting.created_by is not None:
            plan = (await self.quota_service.subscriptions.get_current(meeting.created_by)).plan
            limit_seconds = plan.total_duration_limit_minutes * 60
            if limit_seconds > 0 and metadata.duration_seconds > limit_seconds:
                return "The recording is longer than the maximum allowed by your plan."
        return None

    async def _summarize(self, job: ProcessingJobModel, meeting: MeetingModel) -> StepOutcome:
        segments = await self._load_segments(meeting.id)
        if not segments:
            meeting.summary_status = SummaryStatus.FAILED
            job.status = JobStatus.FAILED
            job.error = "The transcript is empty."
            await self._finish_if_complete(meeting, job)
            return StepOutcome()

        transcript = "\n".join(f"{s.speaker_label}: {s.content}" for s in segments)
        result = await self.ai_client.summarize(str(meeting.id), transcript)

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
        await self._finish_if_complete(meeting, job)
        return StepOutcome()

    async def _index(self, job: ProcessingJobModel, meeting: MeetingModel) -> StepOutcome:
        if meeting.index_status == IndexStatus.READY:
            return StepOutcome()
        await self.indexer.rebuild_index(meeting.id, meeting.transcript_revision)
        meeting.index_status = IndexStatus.READY
        await self._finish_if_complete(meeting, job)
        return StepOutcome()

    async def _handle_ai_failure(
        self, job: ProcessingJobModel, meeting: MeetingModel, exc: AIUnavailableError
    ) -> StepOutcome:
        """Retry transient failures with backoff, otherwise record a permanent failure."""
        job.attempts += 1
        if exc.retryable and job.attempts < self.settings.max_attempts:
            job.status = JobStatus.PENDING
            job.error = exc.message
            return StepOutcome(retry_in=self.settings.retry_base_seconds * 2 ** (job.attempts - 1))

        logger.warning(
            "processing_job_failed", job_id=str(job.id), kind=job.kind, reason=exc.message
        )
        job.status = JobStatus.FAILED
        job.error = exc.message
        job.finished_at = self.clock()
        if job.kind == JobKind.TRANSCRIBE:
            await self._fail_meeting(meeting, "transcribe", exc.message)
        elif job.kind == JobKind.SUMMARIZE:
            meeting.summary_status = SummaryStatus.FAILED
            await self._finish_if_complete(meeting, job)
        elif job.kind == JobKind.INDEX:
            meeting.index_status = IndexStatus.FAILED
            await self._finish_if_complete(meeting, job)
        return StepOutcome()

    async def _fail_transcription(
        self, job: ProcessingJobModel, meeting: MeetingModel, stage: str, reason: str
    ) -> StepOutcome:
        job.status = JobStatus.FAILED
        job.error = reason
        job.finished_at = self.clock()
        await self._fail_meeting(meeting, stage, reason)
        return StepOutcome()

    async def _fail_meeting(self, meeting: MeetingModel, stage: str, reason: str) -> None:
        logger.warning(
            "meeting_processing_failed", meeting_id=str(meeting.id), stage=stage, reason=reason
        )
        transition(meeting, MeetingStatus.FAILED, failure_stage=stage, failure_reason=reason)

    async def _finish_if_complete(self, meeting: MeetingModel, job: ProcessingJobModel) -> None:
        """Mark the meeting ready once neither summary nor index is still pending, then charge quota."""
        still_pending = (
            meeting.summary_status == SummaryStatus.PENDING
            or meeting.index_status == IndexStatus.PENDING
        )
        if still_pending or meeting.status != MeetingStatus.SUMMARIZING:
            return
        transition(meeting, MeetingStatus.READY)
        if meeting.created_by is not None and job.audio_file_id is not None:
            audio = await self.session.get(AudioFileModel, job.audio_file_id)
            if audio is not None:
                await self.quota_service.record_usage(
                    user_id=meeting.created_by,
                    meeting_id=meeting.id,
                    duration_seconds=audio.duration_seconds,
                    audio_file_id=audio.id,
                )

    async def _load_segments(self, meeting_id: uuid.UUID) -> list[TranscriptSegmentModel]:
        result = await self.session.scalars(
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.meeting_id == meeting_id)
            .order_by(TranscriptSegmentModel.sequence_order)
        )
        return list(result.all())

    async def _replace_segments(self, meeting: MeetingModel, segments: list[dict]) -> None:
        """Replace all transcript segments so reruns never duplicate rows, and bump the revision."""
        await self.session.execute(
            delete(TranscriptSegmentModel).where(TranscriptSegmentModel.meeting_id == meeting.id)
        )
        await self.session.flush()
        for order, segment in enumerate(segments, start=1):
            self.session.add(
                TranscriptSegmentModel(
                    meeting_id=meeting.id,
                    speaker_label=str(segment.get("speaker", "Speaker 1")),
                    start_time=float(segment.get("start", 0.0)),
                    end_time=float(segment.get("end", 0.0)),
                    content=str(segment.get("text", "")),
                    sequence_order=order,
                )
            )
        meeting.transcript_revision += 1
        await self.session.flush()
