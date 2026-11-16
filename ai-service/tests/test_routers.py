import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_audio_process_router() -> None:
    """Verify /audio/process endpoint returns structured segments."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/audio/process",
            json={"meeting_id": "test-uuid-1234", "audio_path": "sample.wav", "language": "vi"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meeting_id"] == "test-uuid-1234"
        assert data["status"] == "completed"
        assert data["segments_count"] >= 2
        assert len(data["segments"]) >= 2
        first_seg = data["segments"][0]
        assert "speaker" in first_seg
        assert "start" in first_seg
        assert "end" in first_seg
        assert "words" in first_seg


@pytest.mark.asyncio
async def test_rag_summarize_router() -> None:
    """Verify /rag/summarize endpoint returns structured summary."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/rag/summarize",
            json={
                "meeting_id": "test-uuid-1234",
                "full_transcript": "SPEAKER_00: Chào mọi người.\nSPEAKER_01: Bắt đầu họp.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "executive_summary" in data
        assert "key_points" in data
        assert "action_items" in data
