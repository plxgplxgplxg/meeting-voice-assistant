import pytest
from app.rag.generator import RAGAnswerGenerator


def test_format_excerpts() -> None:
    """Verify that context segments are formatted into XML excerpts with tags."""
    generator = RAGAnswerGenerator()
    segments = [
        {
            "segment_id": "seg-1",
            "speaker": "SPEAKER_00",
            "start": 10.0,
            "end": 25.0,
            "text": "Dự án cần hoàn thành trước ngày 15/11.",
        },
        {
            "segment_id": "seg-2",
            "speaker": "SPEAKER_01",
            "start": 26.0,
            "end": 40.0,
            "text": "Bên kiểm thử cần 3 ngày chạy test.",
        },
    ]

    excerpts = generator.format_excerpts(segments)
    assert "<excerpts>" in excerpts
    assert "</excerpts>" in excerpts
    assert "[S01]" in excerpts
    assert "[S02]" in excerpts
    assert "SPEAKER_00" in excerpts
    assert "15/11" in excerpts


@pytest.mark.asyncio
async def test_answer_query_fallback() -> None:
    """Ensure fallback answer and citation extraction works when API key is empty."""
    generator = RAGAnswerGenerator(provider="gemini")
    segments = [
        {
            "segment_id": "seg-1",
            "speaker": "SPEAKER_00",
            "start": 10.0,
            "end": 25.0,
            "text": "Thống nhất sử dụng Gladia API và Gemini 2.0 Flash.",
        }
    ]

    result = await generator.answer_query(
        query="Cuộc họp thống nhất sử dụng model gì?",
        context_segments=segments,
    )

    assert "answer" in result
    assert "citations" in result
    assert len(result["citations"]) == 1
    assert result["citations"][0]["segment_id"] == "seg-1"
    assert result["citations"][0]["speaker_label"] == "SPEAKER_00"
    assert result["citations"][0]["start_time"] == 10.0
