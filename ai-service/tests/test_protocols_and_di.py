from typing import Any

import httpx
import pytest

from app.pipelines.protocols import AudioProcessorProtocol
from app.rag.generator import MeetingSummaryGenerator, RAGAnswerGenerator
from app.rag.llm_client import OpenAICompatibleLLMClient
from app.rag.protocols import EmbeddingProviderProtocol, LLMClientProtocol
from app.rag.retriever import MeetingRetriever


class MockAudioProcessor(AudioProcessorProtocol):
    """Mock audio processor implementing AudioProcessorProtocol."""

    def __init__(self, segments: list[dict[str, Any]] | None = None) -> None:
        self.segments = segments or [
            {
                "segment_id": 0,
                "speaker": "SPEAKER_00",
                "start": 0.0,
                "end": 2.0,
                "text": "Kiểm thử pipeline âm thanh.",
                "confidence": 0.99,
                "words": [],
            }
        ]

    async def process_audio(
        self,
        audio_path: str,
        language: str = "vi",
        min_speakers: int = 1,
        max_speakers: int = 6,
    ) -> list[dict[str, Any]]:
        return self.segments


class MockLLMClient(LLMClientProtocol):
    """Mock LLM client implementing LLMClientProtocol."""

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_messages: list[dict[str, str]] = []

    async def generate_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        self.last_messages = messages
        return self.response_text


class MockEmbeddingProvider(EmbeddingProviderProtocol):
    """Mock embedding provider implementing EmbeddingProviderProtocol."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        # Return simple orthogonal or deterministic vectors
        result: list[list[float]] = []
        for text in texts:
            if "quan trọng" in text:
                result.append([1.0, 0.0, 0.0])
            else:
                result.append([0.0, 1.0, 0.0])
        return result


@pytest.mark.asyncio
async def test_audio_processor_satisfies_protocol() -> None:
    """A custom AudioProcessorProtocol implementation is accepted wherever a processor is needed."""
    mock_processor = MockAudioProcessor()
    assert isinstance(mock_processor, AudioProcessorProtocol)

    segments = await mock_processor.process_audio("fake.wav")
    assert segments[0]["speaker"] == "SPEAKER_00"


@pytest.mark.asyncio
async def test_llm_client_dependency_injection_summary() -> None:
    """Verify that custom LLMClientProtocol can be injected into MeetingSummaryGenerator."""
    mock_json = (
        '{"executive_summary": "Tóm tắt từ mock LLM.", '
        '"key_points": ["Điểm 1"], '
        '"action_items": [{"description": "Task 1", "assignee": "A", "status": "pending"}]}'
    )
    mock_client = MockLLMClient(response_text=mock_json)

    generator = MeetingSummaryGenerator(llm_client=mock_client)
    summary = await generator.generate_summary("Transcript cuộc họp...")

    assert summary["executive_summary"] == "Tóm tắt từ mock LLM."
    assert len(summary["key_points"]) == 1
    assert summary["key_points"][0] == "Điểm 1"
    assert len(summary["action_items"]) == 1
    assert summary["action_items"][0]["description"] == "Task 1"


@pytest.mark.asyncio
async def test_llm_client_dependency_injection_rag() -> None:
    """Verify that custom LLMClientProtocol can be injected into RAGAnswerGenerator."""
    mock_answer = "Theo cuộc họp [S01], hệ thống sẽ triển khai vào thứ hai."
    mock_client = MockLLMClient(response_text=mock_answer)

    generator = RAGAnswerGenerator(llm_client=mock_client)
    segments = [
        {
            "segment_id": "seg-10",
            "speaker": "Nguyen Van A",
            "start": 12.0,
            "end": 20.0,
            "text": "Thứ hai tới hệ thống sẽ triển khai chính thức.",
        }
    ]

    result = await generator.answer_query(
        query="Khi nào hệ thống triển khai?",
        context_segments=segments,
    )

    assert result["answer"] == mock_answer
    assert len(result["citations"]) == 1
    assert result["citations"][0]["segment_id"] == "seg-10"
    assert result["citations"][0]["speaker_label"] == "Nguyen Van A"


@pytest.mark.asyncio
async def test_openai_compatible_llm_client_transport() -> None:
    """Verify OpenAICompatibleLLMClient against custom httpx mock transport."""
    def handler(request: httpx.Request) -> httpx.Response:
        content = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Phản hồi thử nghiệm từ mock server.",
                    }
                }
            ]
        }
        return httpx.Response(200, json=content)

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        llm_client = OpenAICompatibleLLMClient(
            provider="gemini",
            api_key="mock_key",
            client=client,
        )
        assert llm_client.is_available is True
        response = await llm_client.generate_chat_completion(
            messages=[{"role": "user", "content": "Xin chào"}]
        )
        assert response == "Phản hồi thử nghiệm từ mock server."


@pytest.mark.asyncio
async def test_embedding_provider_dependency_injection() -> None:
    """Verify that custom EmbeddingProviderProtocol can be injected into MeetingRetriever."""
    mock_provider = MockEmbeddingProvider()
    retriever = MeetingRetriever(embedding_provider=mock_provider)

    segments = [
        {"segment_id": "1", "speaker": "A", "start": 0.0, "end": 5.0, "text": "Đoạn thông tin quan trọng."},
        {"segment_id": "2", "speaker": "B", "start": 6.0, "end": 10.0, "text": "Đoạn bình thường không có từ khóa."},
    ]

    results = await retriever.retrieve(query="nội dung quan trọng", segments=segments, top_k=1)
    assert len(results) == 1
    assert results[0]["segment_id"] == "1"
