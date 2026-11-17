import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import JobKind, JobStatus
from app.models.processing_job import ProcessingJobModel
from app.services.processing.outbox import OutboxService

RUN_JOB_TASK = "run_processing_job"


class JobService:
    """Creates processing jobs idempotently and queues them through the outbox."""

    def __init__(self, session: AsyncSession, outbox: OutboxService | None = None) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            outbox: Outbox writer; defaults to one on ``session``.
        """
        self.session = session
        self.outbox = outbox or OutboxService(session)

    async def enqueue(
        self,
        meeting_id: uuid.UUID,
        kind: JobKind,
        idempotency_key: str,
        audio_file_id: uuid.UUID | None = None,
        delay_seconds: float = 0,
    ) -> tuple[ProcessingJobModel, bool]:
        """Create a job and its outbox event unless one with the same key exists.

        Args:
            meeting_id: Meeting the job works on.
            kind: Job kind.
            idempotency_key: Unique key; repeating it returns the existing job.
            audio_file_id: Audio file the job processes, if any.
            delay_seconds: Delay before the job is published to the broker.

        Returns:
            Tuple of the job and whether it was newly created.
        """
        existing = await self._find(idempotency_key)
        if existing is not None:
            return existing, False

        job = ProcessingJobModel(
            meeting_id=meeting_id,
            audio_file_id=audio_file_id,
            kind=kind,
            status=JobStatus.PENDING,
            idempotency_key=idempotency_key,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(job)
                await self.session.flush()
        except IntegrityError:
            existing = await self._find(idempotency_key)
            assert existing is not None
            return existing, False

        await self.outbox.enqueue(RUN_JOB_TASK, [str(job.id)], delay_seconds)
        return job, True

    async def _find(self, idempotency_key: str) -> ProcessingJobModel | None:
        return await self.session.scalar(
            select(ProcessingJobModel).where(ProcessingJobModel.idempotency_key == idempotency_key)
        )
