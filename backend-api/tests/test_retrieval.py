import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript import TranscriptSegmentModel
from app.models.transcript_chunk import TranscriptChunkModel
from app.services.retrieval_service import RetrievalService
from tests.conftest import TEST_DATABASE_URL, FakeAIClient, MakeMeeting

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="pgvector retrieval requires PostgreSQL (set TEST_DATABASE_URL)"
)

TURNS = [
    ("Linh", "Ngân sách marketing quý này tăng hai mươi phần trăm"),
    ("Dũng", "Kiến trúc API-first giúp backend tách khỏi frontend"),
    ("Linh", "Hạn chót nộp báo cáo tài chính là thứ sáu tuần sau"),
    ("Dũng", "Gladia xử lý nhận dạng giọng nói và phân tách người nói"),
]


async def seed_meeting(db: AsyncSession, make_meeting: MakeMeeting) -> uuid.UUID:
    meeting = await make_meeting(None)
    for order, (speaker, text) in enumerate(TURNS, start=1):
        db.add(
            TranscriptSegmentModel(
                meeting_id=meeting.id, speaker_label=speaker, start_time=order * 10.0,
                end_time=order * 10.0 + 5, content=text, sequence_order=order,
            )
        )
    await db.flush()
    return meeting.id


@pytest.mark.asyncio
async def test_index_then_hybrid_search_ranks_the_relevant_turn_first(
    db_session: AsyncSession, make_meeting: MakeMeeting, fake_ai: FakeAIClient
) -> None:
    meeting_id = await seed_meeting(db_session, make_meeting)
    service = RetrievalService(db_session, fake_ai)

    assert await service.rebuild_index(meeting_id, revision=3) == 4
    chunks = await service.search(meeting_id, "ngân sách marketing", k=3)

    assert chunks[0].text.startswith("Ngân sách marketing")
    assert chunks[0].speaker_label == "Linh" and len(chunks[0].segment_ids) == 1
    assert len(chunks) <= 3
    assert all(a.score >= b.score for a, b in zip(chunks, chunks[1:], strict=False))
    assert ("query", ["ngân sách marketing"]) in fake_ai.embedded


@pytest.mark.asyncio
async def test_lexical_match_is_found_even_when_dense_similarity_is_weak(
    db_session: AsyncSession, make_meeting: MakeMeeting, fake_ai: FakeAIClient
) -> None:
    """A rare exact term (full-text stream) still surfaces its chunk through the fusion."""
    meeting_id = await seed_meeting(db_session, make_meeting)
    service = RetrievalService(db_session, fake_ai)
    await service.rebuild_index(meeting_id, 1)

    chunks = await service.search(meeting_id, "Gladia", k=2)

    assert chunks and "Gladia" in chunks[0].text


@pytest.mark.asyncio
async def test_search_is_scoped_to_one_meeting(
    db_session: AsyncSession, make_meeting: MakeMeeting, fake_ai: FakeAIClient
) -> None:
    mine = await seed_meeting(db_session, make_meeting)
    other = await seed_meeting(db_session, make_meeting)
    service = RetrievalService(db_session, fake_ai)
    await service.rebuild_index(mine, 1)
    await service.rebuild_index(other, 1)

    chunks = await service.search(mine, "ngân sách", k=10)

    owners = {
        row for row in (
            await db_session.scalars(
                select(TranscriptChunkModel.meeting_id).where(
                    TranscriptChunkModel.id.in_([c.id for c in chunks])
                )
            )
        )
    }
    assert owners == {mine}


@pytest.mark.asyncio
async def test_rebuilding_replaces_chunks_instead_of_duplicating_them(
    db_session: AsyncSession, make_meeting: MakeMeeting, fake_ai: FakeAIClient
) -> None:
    meeting_id = await seed_meeting(db_session, make_meeting)
    service = RetrievalService(db_session, fake_ai)

    await service.rebuild_index(meeting_id, 1)
    await service.rebuild_index(meeting_id, 2)

    count = await db_session.scalar(
        select(func.count()).select_from(TranscriptChunkModel).where(
            TranscriptChunkModel.meeting_id == meeting_id
        )
    )
    revisions = set(await db_session.scalars(select(TranscriptChunkModel.transcript_revision)))
    assert count == 4 and revisions == {2}


@pytest.mark.asyncio
async def test_search_payload_to_the_ai_service_is_bounded_by_k_not_transcript_length(
    db_session: AsyncSession, make_meeting: MakeMeeting, fake_ai: FakeAIClient
) -> None:
    """A long meeting still yields at most k chunks, so the answer call stays constant size."""
    meeting = await make_meeting(None)
    for order in range(1, 301):
        db_session.add(
            TranscriptSegmentModel(
                meeting_id=meeting.id, speaker_label=f"S{order % 3}", start_time=order * 5.0,
                end_time=order * 5.0 + 4, content=f"nội dung số {order} về dự án", sequence_order=order,
            )
        )
    await db_session.flush()
    service = RetrievalService(db_session, fake_ai)
    await service.rebuild_index(meeting.id, 1)

    assert len(await service.search(meeting.id, "dự án", k=5)) == 5
