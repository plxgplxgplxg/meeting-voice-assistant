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
from app.domain.enums import MeetingStatus
from app.models.meeting import MeetingModel
from app.services.billing.quota_service import QuotaService
from app.services.processing.pipeline import MeetingProcessingPipeline
from app.services.processing.state import transition

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
    return MeetingProcessingPipeline(session, ai_client, QuotaService(session))


async def run_meeting_pipeline(
    meeting_id: uuid.UUID, audio_file_id: uuid.UUID, http_client: httpx.AsyncClient
) -> str:
    """Run the processing pipeline in its own transaction.

    If an unexpected error escapes the pipeline, its partial writes are rolled
    back and the meeting is marked ``failed`` in a fresh transaction so the UI
    never polls a meeting that is stuck in a processing state.

    Args:
        meeting_id: Meeting to process.
        audio_file_id: Audio file to transcribe.
        http_client: Shared HTTP client of the worker process.

    Returns:
        Final meeting status value.
    """
    async with async_session_factory() as session:
        try:
            status = await build_pipeline(session, http_client).run(meeting_id, audio_file_id)
            await session.commit()
            return status.value
        except Exception:
            await session.rollback()
            logger.exception("meeting_pipeline_crashed", meeting_id=str(meeting_id))
            await _mark_failed(session, meeting_id)
            raise


async def _mark_failed(session: AsyncSession, meeting_id: uuid.UUID) -> None:
    meeting = await session.get(MeetingModel, meeting_id)
    if meeting is None:
        return
    try:
        transition(
            meeting,
            MeetingStatus.FAILED,
            failure_stage="pipeline",
            failure_reason=INTERNAL_ERROR_REASON,
        )
    except Exception:
        return
    await session.commit()
