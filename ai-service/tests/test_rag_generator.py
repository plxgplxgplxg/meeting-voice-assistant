import pytest

from app.core.errors import ProviderError, ProviderNotConfiguredError
from app.rag.generator import RAGAnswerGenerator


class ScriptedLLM:
    def __init__(self, answer: str = "", error: Exception | None = None) -> None:
        self.answer = answer
        self.error = error

    async def generate_chat_completion(self, messages, temperature: float = 0.2) -> str:
        if self.error:
            raise self.error
        return self.answer


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


SEGMENTS = [
    {
        "segment_id": "seg-1",
        "speaker": "SPEAKER_00",
        "start": 10.0,
        "end": 25.0,
        "text": "Thống nhất sử dụng Gladia API và Gemini 2.0 Flash.",
    }
]


@pytest.mark.asyncio
async def test_answer_query_builds_citations_from_cited_excerpts() -> None:
    """Citation tags in the answer are resolved to the matching segment."""
    generator = RAGAnswerGenerator(llm_client=ScriptedLLM("Dùng Gladia API [S01]."))
    result = await generator.answer_query("Dùng model gì?", SEGMENTS)

    assert len(result["citations"]) == 1
    assert result["citations"][0]["segment_id"] == "seg-1"
    assert result["citations"][0]["speaker_label"] == "SPEAKER_00"
    assert result["citations"][0]["start_time"] == 10.0


@pytest.mark.asyncio
async def test_answer_query_without_llm_key_raises_instead_of_quoting_the_transcript() -> None:
    """No API key means a configuration error, not a quote presented as an answer."""
    generator = RAGAnswerGenerator(provider="gemini")
    generator.llm_client.api_key = ""
    with pytest.raises(ProviderNotConfiguredError):
        await generator.answer_query("Dùng model gì?", SEGMENTS)


@pytest.mark.asyncio
async def test_answer_query_propagates_provider_failures() -> None:
    generator = RAGAnswerGenerator(llm_client=ScriptedLLM(error=ProviderError("boom")))
    with pytest.raises(ProviderError):
        await generator.answer_query("Dùng model gì?", SEGMENTS)


@pytest.mark.asyncio
async def test_answer_query_without_context_says_nothing_was_found() -> None:
    generator = RAGAnswerGenerator(llm_client=ScriptedLLM("unused"))
    result = await generator.answer_query("Dùng model gì?", [])
    assert "không tìm thấy" in result["answer"]
    assert result["citations"] == []
