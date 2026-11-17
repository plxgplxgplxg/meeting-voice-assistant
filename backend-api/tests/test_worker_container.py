import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models.audio_file import AudioFileModel
from app.models.meeting import MeetingModel
from app.models.user import UserModel
from app.workers import container
from app.workers.container import INTERNAL_ERROR_REASON, run_meeting_pipeline


class ExplodingPipeline:
    async def run(self, meeting_id: uuid.UUID, audio_file_id: uuid.UUID):
        raise RuntimeError("unexpected bug")


@pytest.mark.asyncio
async def test_unexpected_pipeline_crash_marks_meeting_failed(
    test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash rolls back partial work and leaves a failed meeting, never a stuck processing one."""
    factory = async_sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    async with factory() as setup:
        user = UserModel(email="w@example.com", full_name="W", password_hash="x")
        setup.add(user)
        await setup.flush()
        meeting = MeetingModel(title="m", status="uploaded", created_by=user.id)
        setup.add(meeting)
        await setup.flush()
        audio = AudioFileModel(meeting_id=meeting.id, file_name="a.wav", storage_key="k/a.wav")
        setup.add(audio)
        await setup.commit()
        meeting_id, audio_id = meeting.id, audio.id

    monkeypatch.setattr(container, "async_session_factory", factory)
    monkeypatch.setattr(container, "build_pipeline", lambda session, http: ExplodingPipeline())

    async with httpx.AsyncClient() as http_client:
        with pytest.raises(RuntimeError):
            await run_meeting_pipeline(meeting_id, audio_id, http_client)

    async with factory() as check:
        stored = await check.get(MeetingModel, meeting_id)
    assert stored.status == "failed"
    assert stored.failure_stage == "pipeline"
    assert stored.failure_reason == INTERNAL_ERROR_REASON


def test_celery_app_registers_the_processing_task() -> None:
    """The worker entrypoint imports cleanly and exposes the task the dispatcher sends."""
    from app.workers.celery_app import celery_app

    celery_app.loader.import_default_modules()
    assert "process_meeting_task" in celery_app.tasks
    assert celery_app.conf.task_acks_late is True
