import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.errors import AIUnavailableError, ValidationFailedError
from app.domain.enums import JobKind, MeetingStatus
from app.models.audio_file import AudioFileModel
from app.models.billing import MeetingQuotaUsageModel
from app.models.outbox import OutboxEventModel
from app.models.processing_job import ProcessingJobModel
from app.models.summary import ActionItemModel, SummaryModel
from app.models.transcript import TranscriptSegmentModel
from app.services.billing.quota_service import QuotaService
from app.services.event_bus import build_event_bus
from app.services.processing.jobs import JobService
from app.services.processing.pipeline import MeetingProcessingPipeline, PipelineSettings
from app.services.processing.state import transition
from app.services.storage_service import StorageService
from tests.conftest import FakeAIClient, FakeIndexer, FakeProbe, MakeMeeting

SEGMENTS = [
    {"speaker": "SPEAKER_00", "start": 0.0, "end": 30.0, "text": "Xin chào mọi người."},
    {"speaker": "SPEAKER_01", "start": 31.0, "end": 90.0, "text": "Bắt đầu họp thôi."},
]
SUMMARY = {
    "executive_summary": "Cuộc họp khởi động dự án.",
    "key_points": ["Khởi động dự án"],
    "action_items": [{"description": "Gửi lịch họp", "assignee": "Linh", "status": "pending"}],
}


async def uploaded_meeting(db: AsyncSession, make_meeting: MakeMeeting, owner_id: uuid.UUID):
    meeting = await make_meeting(owner_id, status="uploaded")
    audio = AudioFileModel(
        meeting_id=meeting.id,
        file_name="a.wav",
        storage_key=f"{meeting.id}/a.wav",
        file_size_bytes=10,
    )
    db.add(audio)
    await db.flush()
    job, _ = await JobService(db).enqueue(
        meeting.id, JobKind.TRANSCRIBE, f"transcribe:{audio.id}", audio.id
    )
    return meeting, audio, job


def make_pipeline(
    db: AsyncSession,
    ai: FakeAIClient,
    probe: FakeProbe,
    indexer: FakeIndexer,
    storage: StorageService,
    settings: PipelineSettings | None = None,
    clock=utc_now,
) -> MeetingProcessingPipeline:
    return MeetingProcessingPipeline(
        session=db,
        ai_client=ai,
        quota_service=QuotaService(db),
        probe=probe,
        storage=storage,
        indexer=indexer,
        events=build_event_bus(db),
        settings=settings or PipelineSettings(poll_seconds=1, retry_base_seconds=1),
        clock=clock,
    )


async def drain(pipeline: MeetingProcessingPipeline, db: AsyncSession, limit: int = 40) -> int:
    """Run jobs the way workers would until none is left to run, counting executions."""
    runs = 0
    for _ in range(limit):
        pending = (
            await db.scalars(
                select(ProcessingJobModel)
                .where(ProcessingJobModel.status.in_(["pending", "running"]))
                .order_by(ProcessingJobModel.created_at)
            )
        ).all()
        if not pending:
            return runs
        for job in pending:
            await pipeline.run_job(job.id)
            runs += 1
    raise AssertionError("jobs never settled")


@pytest.fixture
def pipe(db_session, fake_ai, fake_probe, fake_indexer, storage):
    return make_pipeline(db_session, fake_ai, fake_probe, fake_indexer, storage)


@pytest.mark.asyncio
async def test_full_run_submits_polls_summarizes_indexes_and_charges_probed_duration(
    db_session, make_meeting, register_user, fake_ai, fake_probe, fake_indexer, pipe
) -> None:
    """transcribe -> (summarize + index) ends ready with real data and one charge by probed duration."""
    owner = await register_user("owner@example.com")
    meeting, audio, _ = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments, fake_ai.summary, fake_ai.pending_polls = SEGMENTS, SUMMARY, 2
    fake_probe.duration = 125.0

    await drain(pipe, db_session)

    assert meeting.status == "ready"
    assert (meeting.summary_status, meeting.index_status) == ("ready", "ready")
    assert meeting.transcript_revision == 1
    assert fake_ai.submissions == [audio.storage_key] and fake_ai.polls == 3
    assert fake_indexer.rebuilt == [(meeting.id, 1)]
    segments = (await db_session.scalars(select(TranscriptSegmentModel))).all()
    assert [s.content for s in sorted(segments, key=lambda s: s.sequence_order)] == [
        "Xin chào mọi người.",
        "Bắt đầu họp thôi.",
    ]
    usage = (await db_session.scalars(select(MeetingQuotaUsageModel))).all()
    assert [u.duration_seconds for u in usage] == [125.0]
    assert audio.duration_seconds == 125.0


@pytest.mark.asyncio
async def test_each_step_is_a_separate_job_and_http_calls_never_wait_for_the_provider(
    db_session, make_meeting, register_user, fake_ai, pipe
) -> None:
    """The first run only submits and asks to be polled again, so no request stays open."""
    owner = await register_user("owner@example.com")
    meeting, _, job = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments, fake_ai.summary, fake_ai.pending_polls = SEGMENTS, SUMMARY, 1

    first = await pipe.run_job(job.id)
    assert first.retry_in == 1 and job.provider_job_id == "prov-1"
    assert meeting.status == "transcribing" and fake_ai.polls == 0

    second = await pipe.run_job(job.id)
    assert second.retry_in == 1 and fake_ai.polls == 1

    third = await pipe.run_job(job.id)
    assert third.done and job.status == "succeeded"
    kinds = sorted(
        j.kind for j in (await db_session.scalars(select(ProcessingJobModel))).all()
    )
    assert kinds == ["index", "summarize", "transcribe"]


@pytest.mark.asyncio
async def test_missing_asr_provider_fails_meeting_without_charging_or_inventing_data(
    db_session, make_meeting, register_user, fake_ai, pipe
) -> None:
    """A permanent provider error ends failed with the reason, nothing fake is stored, no quota used."""
    owner = await register_user("owner@example.com")
    meeting, _, job = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.submit_error = AIUnavailableError("ASR provider not configured")

    await drain(pipe, db_session)

    assert meeting.status == "failed"
    assert (meeting.failure_stage, meeting.failure_reason) == ("transcribe", "ASR provider not configured")
    assert job.status == "failed"
    assert await db_session.scalar(select(func.count()).select_from(TranscriptSegmentModel)) == 0
    assert await db_session.scalar(select(func.count()).select_from(SummaryModel)) == 0
    assert await db_session.scalar(select(func.count()).select_from(MeetingQuotaUsageModel)) == 0


@pytest.mark.asyncio
async def test_transient_errors_retry_with_backoff_then_succeed(
    db_session, make_meeting, register_user, fake_ai, pipe
) -> None:
    """A retryable failure is retried with exponential backoff and counted on the job."""
    owner = await register_user("owner@example.com")
    meeting, _, job = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments, fake_ai.summary = SEGMENTS, SUMMARY
    fake_ai.submit_error = AIUnavailableError("down", retryable=True)

    first = await pipe.run_job(job.id)
    second = await pipe.run_job(job.id)
    assert (first.retry_in, second.retry_in) == (1, 2)
    assert job.attempts == 2 and job.status == "pending"

    fake_ai.submit_error = None
    await drain(pipe, db_session)
    assert meeting.status == "ready"


@pytest.mark.asyncio
async def test_retries_stop_after_max_attempts_and_fail_the_meeting(
    db_session, make_meeting, register_user, fake_ai, pipe
) -> None:
    owner = await register_user("owner@example.com")
    meeting, _, job = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.submit_error = AIUnavailableError("still down", retryable=True)

    await drain(pipe, db_session)

    assert job.attempts == 3 and job.status == "failed"
    assert meeting.status == "failed" and meeting.failure_reason == "still down"


@pytest.mark.asyncio
async def test_transcription_that_never_finishes_times_out(
    db_session, make_meeting, register_user, fake_ai, fake_probe, fake_indexer, storage
) -> None:
    owner = await register_user("owner@example.com")
    meeting, _, job = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.pending_polls = 10_000
    now = [utc_now()]
    pipe = make_pipeline(
        db_session, fake_ai, fake_probe, fake_indexer, storage,
        PipelineSettings(poll_seconds=1, max_wait_seconds=60), clock=lambda: now[0],
    )

    await pipe.run_job(job.id)
    now[0] += timedelta(seconds=61)
    outcome = await pipe.run_job(job.id)

    assert outcome.done and meeting.status == "failed"
    assert meeting.failure_reason == "Transcription timed out."


@pytest.mark.asyncio
async def test_empty_transcript_fails_instead_of_completing(
    db_session, make_meeting, register_user, fake_ai, pipe
) -> None:
    owner = await register_user("owner@example.com")
    meeting, _, _ = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments = []

    await drain(pipe, db_session)

    assert meeting.status == "failed" and "No speech" in meeting.failure_reason


@pytest.mark.asyncio
async def test_invalid_audio_is_rejected_by_the_probe_before_any_ai_call(
    db_session, make_meeting, register_user, fake_ai, fake_probe, pipe
) -> None:
    owner = await register_user("owner@example.com")
    meeting, _, _ = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_probe.error = ValidationFailedError("The file contains no audio stream.")

    await drain(pipe, db_session)

    assert (meeting.status, meeting.failure_stage) == ("failed", "probe")
    assert fake_ai.submissions == []


@pytest.mark.asyncio
async def test_recording_longer_than_the_plan_limit_is_rejected(
    db_session, make_meeting, register_user, fake_ai, fake_probe, pipe
) -> None:
    """The Free plan allows 60 minutes in total, so a 61 minute file can never succeed."""
    owner = await register_user("owner@example.com")
    meeting, _, _ = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_probe.duration = 61 * 60

    await drain(pipe, db_session)

    assert meeting.status == "failed" and "plan" in meeting.failure_reason
    assert fake_ai.submissions == []


@pytest.mark.asyncio
async def test_summary_failure_keeps_transcript_and_marks_summary_failed(
    db_session, make_meeting, register_user, fake_ai, pipe
) -> None:
    """A failing LLM never produces a hardcoded summary; the meeting still becomes ready and is charged."""
    owner = await register_user("owner@example.com")
    meeting, _, _ = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments = SEGMENTS
    fake_ai.summary_error = AIUnavailableError("LLM down")

    await drain(pipe, db_session)

    assert meeting.status == "ready"
    assert (meeting.summary_status, meeting.index_status) == ("failed", "ready")
    assert await db_session.scalar(select(func.count()).select_from(SummaryModel)) == 0
    assert await db_session.scalar(select(func.count()).select_from(MeetingQuotaUsageModel)) == 1


@pytest.mark.asyncio
async def test_index_failure_keeps_meeting_usable_and_is_reported(
    db_session, make_meeting, register_user, fake_ai, fake_indexer, pipe
) -> None:
    owner = await register_user("owner@example.com")
    meeting, _, _ = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments, fake_ai.summary = SEGMENTS, SUMMARY
    fake_indexer.error = AIUnavailableError("embedding model unavailable")

    await drain(pipe, db_session)

    assert meeting.status == "ready" and meeting.index_status == "failed"
    assert meeting.summary_status == "ready"


@pytest.mark.asyncio
async def test_rerunning_a_finished_job_is_a_no_op_and_reprocessing_is_idempotent(
    db_session, make_meeting, register_user, fake_ai, pipe
) -> None:
    """Redelivery of a finished job does nothing; reprocessing replaces rows, keeps user items, charges once."""
    owner = await register_user("owner@example.com")
    meeting, audio, job = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments, fake_ai.summary = SEGMENTS, SUMMARY
    await drain(pipe, db_session)
    assert (await pipe.run_job(job.id)).done and fake_ai.polls == 1

    db_session.add(ActionItemModel(meeting_id=meeting.id, description="Mine", source="user"))
    await db_session.flush()
    transition(meeting, MeetingStatus.UPLOADED)
    await JobService(db_session).enqueue(
        meeting.id, JobKind.TRANSCRIBE, f"transcribe:{audio.id}:again", audio.id
    )
    fake_ai.provider_job_id = "prov-2"
    await drain(pipe, db_session)

    assert meeting.status == "ready" and meeting.transcript_revision == 2
    assert await db_session.scalar(select(func.count()).select_from(TranscriptSegmentModel)) == 2
    assert await db_session.scalar(select(func.count()).select_from(SummaryModel)) == 1
    items = (await db_session.scalars(select(ActionItemModel))).all()
    assert sorted(i.source for i in items) == ["ai", "user"]
    assert await db_session.scalar(select(func.count()).select_from(MeetingQuotaUsageModel)) == 1


@pytest.mark.asyncio
async def test_demo_transcription_flags_the_meeting(
    db_session, make_meeting, register_user, fake_ai, pipe
) -> None:
    owner = await register_user("owner@example.com")
    meeting, _, _ = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments, fake_ai.summary, fake_ai.is_demo = SEGMENTS, SUMMARY, True

    await drain(pipe, db_session)

    assert meeting.is_demo is True


@pytest.mark.asyncio
async def test_job_enqueue_is_idempotent_and_writes_one_outbox_event(db_session, make_meeting) -> None:
    meeting = await make_meeting(None, status="uploaded")
    jobs = JobService(db_session)

    first, created_first = await jobs.enqueue(meeting.id, JobKind.INDEX, "index:k")
    second, created_second = await jobs.enqueue(meeting.id, JobKind.INDEX, "index:k")

    assert (created_first, created_second) == (True, False) and first.id == second.id
    events = (await db_session.scalars(select(OutboxEventModel))).all()
    assert [(e.task_name, e.payload) for e in events] == [("run_processing_job", {"args": [str(first.id)]})]
