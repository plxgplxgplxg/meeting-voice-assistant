import asyncio
import uuid
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

import httpx
import structlog
from celery.signals import worker_process_init, worker_process_shutdown
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_service_client import HttpAIServiceClient
from app.core.config import settings
from app.core.database import async_session_factory, engine
from app.domain.enums import JobStatus, MeetingStatus
from app.models.meeting import MeetingModel
from app.models.processing_job import ProcessingJobModel
from app.services.audio_probe import FfprobeAudioProbe
from app.services.billing.quota_service import QuotaService
from app.services.event_bus import build_event_bus
from app.services.processing.outbox import CeleryTaskSender, OutboxRelay
from app.services.processing.pipeline import (
    MeetingProcessingPipeline,
    PipelineSettings,
    StepOutcome,
)
from app.services.processing.state import transition
from app.services.retrieval_service import RetrievalService
from app.services.storage_service import StorageService

logger = structlog.get_logger(__name__)

T = TypeVar("T")

INTERNAL_ERROR_REASON = "Internal processing error. Please retry."


class WorkerRuntime:
    """Per-process event loop and shared HTTP client for Celery workers.

    One ``asyncio.Runner`` lives for the whole worker process so connection
    pools and the HTTP client are reused instead of being rebuilt per task.
    """

    def __init__(self) -> None:
        self.runner: asyncio.Runner | None = None
        self.http_client: httpx.AsyncClient | None = None

    def start(self) -> None:
        """Create the event loop and drop DB connections inherited from the parent process."""
        engine.sync_engine.dispose(close=False)
        self.runner = asyncio.Runner()
        self.http_client = self.runner.run(self._create_client())

    def stop(self) -> None:
        """Close the HTTP client, dispose the engine, and close the event loop."""
        if self.runner is None:
            return
        if self.http_client is not None:
            self.runner.run(self.http_client.aclose())
        self.runner.run(engine.dispose())
        self.runner.close()
        self.runner = None
        self.http_client = None

    def run(self, factory: Callable[[httpx.AsyncClient], Coroutine[Any, Any, T]]) -> T:
        """Run a coroutine on the worker's event loop, starting it on demand.

        Args:
            factory: Builds the coroutine from the process-wide HTTP client.

        Returns:
            The coroutine result.
        """
        if self.runner is None or self.http_client is None:
            self.start()
        assert self.runner is not None and self.http_client is not None
        return self.runner.run(factory(self.http_client))

    @staticmethod
    async def _create_client() -> httpx.AsyncClient:
        return httpx.AsyncClient()


runtime = WorkerRuntime()


@worker_process_init.connect
def _on_worker_process_init(**_: object) -> None:
    runtime.start()


@worker_process_shutdown.connect
def _on_worker_process_shutdown(**_: object) -> None:
    runtime.stop()


def build_pipeline(session: AsyncSession, http_client: httpx.AsyncClient) -> MeetingProcessingPipeline:
    """Wire the processing pipeline with its production collaborators.

    Args:
        session: Session owned by the calling task.
        http_client: Shared HTTP client of the worker process.

    Returns:
        A ready-to-run pipeline.
    """
    ai_client = HttpAIServiceClient(settings.ai_service_url, settings.ai_service_token, http_client)
    return MeetingProcessingPipeline(
        session=session,
        ai_client=ai_client,
        quota_service=QuotaService(session),
        probe=FfprobeAudioProbe(),
        storage=StorageService(),
        indexer=RetrievalService(session, ai_client),
        events=build_event_bus(session),
        settings=PipelineSettings(
            poll_seconds=settings.transcription_poll_seconds,
            max_wait_seconds=settings.transcription_max_wait_seconds,
            max_attempts=settings.job_max_attempts,
            retry_base_seconds=settings.job_retry_base_seconds,
        ),
    )


async def run_processing_job(job_id: uuid.UUID, http_client: httpx.AsyncClient) -> StepOutcome:
    """Run one processing job in its own transaction.

    If an unexpected error escapes the pipeline, its partial writes are rolled
    back and the job and meeting are marked failed in a fresh transaction so the
    UI never polls a meeting that is stuck in a processing state.

    Args:
        job_id: Job to run.
        http_client: Shared HTTP client of the worker process.

    Returns:
        The step outcome, telling the task whether to retry later.
    """
    structlog.contextvars.bind_contextvars(request_id=f"job-{job_id}")
    try:
        async with async_session_factory() as session:
            try:
                outcome = await build_pipeline(session, http_client).run_job(job_id)
                await session.commit()
                return outcome
            except Exception:
                await session.rollback()
                logger.exception("processing_job_crashed", job_id=str(job_id))
                await _mark_failed(session, job_id)
                raise
    finally:
        structlog.contextvars.clear_contextvars()


async def _mark_failed(session: AsyncSession, job_id: uuid.UUID) -> None:
    job = await session.get(ProcessingJobModel, job_id)
    if job is None:
        return
    job.status = JobStatus.FAILED
    job.error = INTERNAL_ERROR_REASON
    meeting = await session.get(MeetingModel, job.meeting_id)
    if meeting is not None:
        try:
            transition(
                meeting,
                MeetingStatus.FAILED,
                failure_stage="pipeline",
                failure_reason=INTERNAL_ERROR_REASON,
            )
        except Exception:
            logger.info("meeting_not_failed_after_crash", meeting_id=str(meeting.id))
    await session.commit()


async def relay_outbox() -> int:
    """Publish pending outbox rows to the broker in their own transaction.

    Returns:
        Number of tasks published.
    """
    async with async_session_factory() as session:
        sent = await OutboxRelay(session, CeleryTaskSender()).dispatch_pending()
        await session.commit()
        return sent
