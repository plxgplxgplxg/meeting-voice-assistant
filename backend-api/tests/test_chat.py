import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AIUnavailableError
from app.models.agent import AgentMessageModel
from app.models.transcript import TranscriptSegmentModel
from app.services.retrieval_service import RetrievedChunk
from tests.conftest import Account, FakeAIClient, FakeRetriever, MakeMeeting, RegisterUser


async def seed_segments(db: AsyncSession, meeting_id) -> TranscriptSegmentModel:
    first = TranscriptSegmentModel(
        meeting_id=meeting_id,
        speaker_label="Linh",
        start_time=0.0,
        end_time=15.0,
        content="Chúng ta thống nhất chuyển toàn bộ sang kiến trúc API-first.",
        sequence_order=1,
    )
    second = TranscriptSegmentModel(
        meeting_id=meeting_id,
        speaker_label="Dũng",
        start_time=16.0,
        end_time=30.0,
        content="Gladia API xử lý ASR và phân tách người nói.",
        sequence_order=2,
    )
    db.add_all([first, second])
    await db.flush()
    return first


@pytest.mark.asyncio
async def test_chat_answer_is_persisted_with_citations(
    client: AsyncClient,
    register_user: RegisterUser,
    make_meeting: MakeMeeting,
    db_session: AsyncSession,
    fake_ai: FakeAIClient,
    fake_retriever: FakeRetriever,
) -> None:
    """A successful RAG answer is stored and returned with its citations."""
    owner = await register_user("owner@example.com")
    meeting = await make_meeting(owner.id)
    segment = await seed_segments(db_session, meeting.id)
    citation = {
        "segment_id": str(segment.id),
        "speaker_label": "Linh",
        "start_time": 0.0,
        "end_time": 15.0,
        "quote": segment.content,
    }
    fake_ai.answer = ("Theo [S01], hệ thống chuyển sang API-first.", [citation])
    fake_retriever.chunks = [
        RetrievedChunk(
            id=uuid.uuid4(), chunk_index=0, speaker_label="Linh", start_time=0.0, end_time=15.0,
            text=segment.content, segment_ids=[segment.id], score=0.9,
        )
    ] * 8

    response = await client.post(
        f"/api/v1/meetings/{meeting.id}/chat",
        headers=owner.headers,
        json={"query": "Kiến trúc mới là gì?"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == "assistant"
    assert body["status"] == "ok"
    assert body["citations"] == [citation]
    assert len(fake_ai.queries[0]["chunks"]) == 5
    assert fake_ai.queries[0]["chunks"][0]["segment_id"] == str(segment.id)
    assert fake_retriever.searches[0][1:] == ("Kiến trúc mới là gì?", 5)

    history = await client.get(
        f"/api/v1/meetings/{meeting.id}/chat/messages", headers=owner.headers
    )
    assert [m["role"] for m in history.json()] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_ai_failure_returns_503_without_fabricated_answer(
    client: AsyncClient,
    register_user: RegisterUser,
    make_meeting: MakeMeeting,
    db_session: AsyncSession,
    fake_ai: FakeAIClient,
) -> None:
    """When the AI service fails, no keyword answer is invented and the error is recorded."""
    owner = await register_user("owner@example.com")
    meeting = await make_meeting(owner.id)
    await seed_segments(db_session, meeting.id)
    fake_ai.query_error = AIUnavailableError("AI service is unreachable.")

    response = await client.post(
        f"/api/v1/meetings/{meeting.id}/chat",
        headers=owner.headers,
        json={"query": "Kiến trúc API-first là gì?"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_UNAVAILABLE"

    messages = (
        await db_session.execute(select(AgentMessageModel).order_by(AgentMessageModel.created_at))
    ).scalars().all()
    assert [(m.role, m.status) for m in messages] == [("user", "ok"), ("assistant", "error")]
    assert "API-first" not in messages[1].content


@pytest.mark.asyncio
async def test_chat_history_is_private_per_user(
    client: AsyncClient,
    register_user: RegisterUser,
    make_meeting: MakeMeeting,
    db_session: AsyncSession,
    fake_ai: FakeAIClient,
) -> None:
    """Two users of the same meeting never see each other's conversation."""
    owner = await register_user("owner@example.com")
    colleague: Account = await register_user("colleague@example.com")
    meeting = await make_meeting(owner.id, share_token="shared-token-abcdefghijklmnop")
    await seed_segments(db_session, meeting.id)
    fake_ai.answer = ("ok [S01]", [])

    await client.post(
        f"/api/v1/meetings/{meeting.id}/chat",
        headers=owner.headers,
        json={"query": "private owner question"},
    )

    seen_by_colleague = await client.get(
        f"/api/v1/meetings/{meeting.id}/chat/messages?share=shared-token-abcdefghijklmnop",
        headers=colleague.headers,
    )
    assert seen_by_colleague.status_code == 200
    assert seen_by_colleague.json() == []


@pytest.mark.asyncio
async def test_asking_before_the_meeting_is_indexed_is_a_conflict(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting
) -> None:
    owner = await register_user("owner@example.com")
    meeting = await make_meeting(owner.id, status="transcribing")

    response = await client.post(
        f"/api/v1/meetings/{meeting.id}/chat", headers=owner.headers, json={"query": "x"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INDEX_NOT_READY"
