import pytest

from app.rag.retriever import MeetingRetriever, cosine_similarity


def test_cosine_similarity() -> None:
    """Verify cosine similarity calculation."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-5

    v3 = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(v1, v3) - 0.0) < 1e-5


@pytest.mark.asyncio
async def test_meeting_retriever_hybrid_ranking() -> None:
    """Verify hybrid search ranks keyword-matching segments higher."""
    retriever = MeetingRetriever()
    segments = [
        {"segment_id": "1", "speaker": "A", "start": 0.0, "end": 5.0, "text": "Hôm nay trời nhiều mây và có thể mưa."},
        {"segment_id": "2", "speaker": "B", "start": 6.0, "end": 12.0, "text": "Về ngân sách dự án quý 4 là năm trăm triệu đồng."},
        {"segment_id": "3", "speaker": "A", "start": 13.0, "end": 20.0, "text": "Tiến độ triển khai hệ thống phần mềm cần hoàn thiện."},
    ]

    results = await retriever.retrieve(query="ngân sách quý 4", segments=segments, top_k=2)
    assert len(results) == 2
    # The segment mentioning "ngân sách" and "quý 4" should be ranked #1
    assert results[0]["segment_id"] == "2"
