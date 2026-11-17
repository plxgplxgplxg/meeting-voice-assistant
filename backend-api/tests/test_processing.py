import itertools
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AIUnavailableError, InvalidStateError
from app.domain.enums import MeetingStatus
from app.models.audio_file import AudioFileModel
from app.models.billing import MeetingQuotaUsageModel
from app.models.meeting import MeetingModel
from app.models.summary import ActionItemModel, SummaryModel
from app.models.transcript import TranscriptSegmentModel
from app.services.billing.quota_service import QuotaService
from app.services.processing.pipeline import MeetingProcessingPipeline
from app.services.processing.state import ALLOWED_TRANSITIONS, transition
from tests.conftest import FakeAIClient, MakeMeeting, RegisterUser

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
    return meeting, audio


def pipeline(db: AsyncSession, ai: FakeAIClient) -> MeetingProcessingPipeline:
    return MeetingProcessingPipeline(db, ai, QuotaService(db))


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (c, t)
        for c, t in itertools.product(MeetingStatus, MeetingStatus)
        if t not in ALLOWED_TRANSITIONS[c]
    ],
)
def test_illegal_transitions_are_rejected(current: MeetingStatus, target: MeetingStatus) -> None:
    """Every move outside the transition table raises InvalidStateError."""
    meeting = MeetingModel(title="t", status=current)
    with pytest.raises(InvalidStateError):
        transition(meeting, target)
    assert meeting.status == current


def test_failed_transition_records_stage_and_reason_and_clears_on_exit() -> None:
    """Entering failed stores the cause, leaving it clears the cause."""
    meeting = MeetingModel(title="t", status=MeetingStatus.TRANSCRIBING)
    transition(meeting, MeetingStatus.FAILED, failure_stage="transcribe", failure_reason="boom")
    assert (meeting.failure_stage, meeting.failure_reason) == ("transcribe", "boom")

    transition(meeting, MeetingStatus.UPLOADED)
    assert meeting.failure_stage is None and meeting.failure_reason is None


@pytest.mark.asyncio
async def test_pipeline_success_produces_transcript_summary_and_charges_quota(
    db_session: AsyncSession, make_meeting: MakeMeeting, register_user: RegisterUser, fake_ai: FakeAIClient
) -> None:
    """A successful run ends ready with real data and one quota charge."""
    owner = await register_user("owner@example.com")
    meeting, audio = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments, fake_ai.summary = SEGMENTS, SUMMARY

    result = await pipeline(db_session, fake_ai).run(meeting.id, audio.id)

    assert result == MeetingStatus.READY
    assert meeting.status == "ready" and meeting.summary_status == "ready"
    assert meeting.duration_seconds == 90.0
    segments = (await db_session.scalars(select(TranscriptSegmentModel))).all()
    assert [s.content for s in sorted(segments, key=lambda s: s.sequence_order)] == [
        "Xin chào mọi người.",
        "Bắt đầu họp thôi.",
    ]
    usage = (await db_session.scalars(select(MeetingQuotaUsageModel))).all()
    assert [u.duration_seconds for u in usage] == [90.0]


@pytest.mark.asyncio
async def test_missing_asr_provider_fails_meeting_without_charging_or_inventing_data(
    db_session: AsyncSession, make_meeting: MakeMeeting, register_user: RegisterUser, fake_ai: FakeAIClient
) -> None:
    """Without a provider the meeting ends failed, nothing fake is stored, and no quota is used."""
    owner = await register_user("owner@example.com")
    meeting, audio = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.audio_error = AIUnavailableError("ASR provider not configured")

    result = await pipeline(db_session, fake_ai).run(meeting.id, audio.id)

    assert result == MeetingStatus.FAILED
    assert meeting.status == "failed"
    assert meeting.failure_stage == "transcribe"
    assert meeting.failure_reason == "ASR provider not configured"
    assert await db_session.scalar(select(func.count()).select_from(TranscriptSegmentModel)) == 0
    assert await db_session.scalar(select(func.count()).select_from(SummaryModel)) == 0
    assert await db_session.scalar(select(func.count()).select_from(MeetingQuotaUsageModel)) == 0


@pytest.mark.asyncio
async def test_empty_transcript_fails_instead_of_completing(
    db_session: AsyncSession, make_meeting: MakeMeeting, register_user: RegisterUser, fake_ai: FakeAIClient
) -> None:
    """An ASR result without speech is a failure, not an empty success."""
    owner = await register_user("owner@example.com")
    meeting, audio = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments = []

    assert await pipeline(db_session, fake_ai).run(meeting.id, audio.id) == MeetingStatus.FAILED
    assert "No speech" in meeting.failure_reason


@pytest.mark.asyncio
async def test_summary_failure_keeps_transcript_and_marks_summary_failed(
    db_session: AsyncSession, make_meeting: MakeMeeting, register_user: RegisterUser, fake_ai: FakeAIClient
) -> None:
    """A failing LLM never produces a hardcoded summary; the transcript still becomes ready."""
    owner = await register_user("owner@example.com")
    meeting, audio = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments = SEGMENTS
    fake_ai.summary_error = AIUnavailableError("LLM down")

    result = await pipeline(db_session, fake_ai).run(meeting.id, audio.id)

    assert result == MeetingStatus.READY
    assert meeting.summary_status == "failed"
    assert await db_session.scalar(select(func.count()).select_from(SummaryModel)) == 0
    assert await db_session.scalar(select(func.count()).select_from(MeetingQuotaUsageModel)) == 1


@pytest.mark.asyncio
async def test_rerun_is_idempotent_and_keeps_user_action_items(
    db_session: AsyncSession, make_meeting: MakeMeeting, register_user: RegisterUser, fake_ai: FakeAIClient
) -> None:
    """Reprocessing replaces segments, upserts the summary, and never charges twice."""
    owner = await register_user("owner@example.com")
    meeting, audio = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments, fake_ai.summary = SEGMENTS, SUMMARY
    runner = pipeline(db_session, fake_ai)

    await runner.run(meeting.id, audio.id)
    db_session.add(
        ActionItemModel(meeting_id=meeting.id, description="Mine", source="user")
    )
    await db_session.flush()
    transition(meeting, MeetingStatus.TRANSCRIBING)
    meeting.status = "uploaded"  # simulate a retry request resetting the state
    await runner.run(meeting.id, audio.id)

    assert await db_session.scalar(select(func.count()).select_from(TranscriptSegmentModel)) == 2
    assert await db_session.scalar(select(func.count()).select_from(SummaryModel)) == 1
    items = (await db_session.scalars(select(ActionItemModel))).all()
    assert sorted(i.source for i in items) == ["ai", "user"]
    assert await db_session.scalar(select(func.count()).select_from(MeetingQuotaUsageModel)) == 1


@pytest.mark.asyncio
async def test_demo_transcription_flags_the_meeting(
    db_session: AsyncSession, make_meeting: MakeMeeting, register_user: RegisterUser, fake_ai: FakeAIClient
) -> None:
    """Meetings processed by the development mock engine are labelled as demo data."""
    owner = await register_user("owner@example.com")
    meeting, audio = await uploaded_meeting(db_session, make_meeting, owner.id)
    fake_ai.segments, fake_ai.summary, fake_ai.is_demo = SEGMENTS, SUMMARY, True

    await pipeline(db_session, fake_ai).run(meeting.id, audio.id)

    assert meeting.is_demo is True
