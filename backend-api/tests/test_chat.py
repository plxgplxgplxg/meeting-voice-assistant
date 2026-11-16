import uuid
from datetime import datetime
import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import MeetingModel
from app.models.transcript import TranscriptSegmentModel
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_chat_service_and_endpoint_flow(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test ChatService and chat API endpoint flow end-to-end.

    Args:
        client: AsyncClient for API endpoints.
        db_session: Database session fixture to seed meeting data.
    """
    meeting_id = uuid.uuid4()
    meeting = MeetingModel(
        id=meeting_id,
        title="Họp Bàn Kiến Trúc Hệ Thống",
        status="completed",
        duration_seconds=180.0,
        created_at=datetime.utcnow(),
    )
    db_session.add(meeting)

    seg1 = TranscriptSegmentModel(
        meeting_id=meeting_id,
        speaker_label="Nguyen Phuong Linh",
        start_time=0.0,
        end_time=15.0,
        content="Chúng ta thống nhất chuyển toàn bộ sang kiến trúc API-first.",
        sequence_order=0,
    )
    seg2 = TranscriptSegmentModel(
        meeting_id=meeting_id,
        speaker_label="Cao Tuan Dung",
        start_time=16.0,
        end_time=30.0,
        content="Gladia API xử lý ASR và phân tách người nói rất chính xác.",
        sequence_order=1,
    )
    db_session.add_all([seg1, seg2])
    await db_session.commit()

    # 1. Test ChatService directly with fallback
    service = ChatService(db_session)
    session = await service.get_or_create_session(meeting_id)
    assert session.meeting_id == meeting_id

    # Ask question using fallback (since AI service is not running in test)
    assistant_msg = await service.ask_question(
        meeting_id=meeting_id,
        query="Cuộc họp thống nhất kiến trúc gì?",
    )
    assert assistant_msg.role == "assistant"
    assert "kiến trúc API-first" in assistant_msg.content
    assert len(assistant_msg.citations) >= 1

    # List messages
    messages = await service.list_messages(meeting_id)
    assert len(messages) >= 2  # user + assistant

    # 2. Test ChatService with mocked AI Service HTTP Client
    def mock_ai_handler(request: httpx.Request) -> httpx.Response:
        data = {
            "answer": "Theo cuộc họp [S01], hệ thống chuyển sang kiến trúc API-first.",
            "citations": [
                {
                    "segment_id": str(seg1.id),
                    "speaker_label": "Nguyen Phuong Linh",
                    "start_time": 0.0,
                    "end_time": 15.0,
                    "quote": "Chúng ta thống nhất chuyển toàn bộ sang kiến trúc API-first.",
                }
            ],
        }
        return httpx.Response(200, json=data)

    mock_transport = httpx.MockTransport(mock_ai_handler)
    async with httpx.AsyncClient(transport=mock_transport) as mock_http:
        service_with_ai = ChatService(
            db_session,
            ai_service_url="http://mock-ai-service",
            http_client=mock_http,
        )
        ai_resp = await service_with_ai.ask_question(
            meeting_id=meeting_id,
            query="Kiến trúc mới là gì?",
        )
        assert "Theo cuộc họp [S01]" in ai_resp.content
        assert len(ai_resp.citations) == 1

    # 3. Test HTTP Endpoint via FastAPI client
    resp = await client.post(
        f"/api/v1/chat/{meeting_id}",
        json={"query": "Gladia có vai trò gì?"},
    )
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["role"] == "assistant"
    assert "Gladia API" in resp_data["content"]
    assert len(resp_data["citations"]) >= 1

    # Retrieve messages via endpoint
    get_resp = await client.get(f"/api/v1/chat/{meeting_id}/messages")
    assert get_resp.status_code == 200
    all_msgs = get_resp.json()
    assert len(all_msgs) >= 4  # multiple rounds of chat
