import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import ai_settings
from app.deps import get_audio_processor, get_embedder, get_llm_client
from app.main import app
from app.pipelines.fake import FakeAudioProcessor
from app.rag.fake import FakeLLMClient

TOKEN = {"X-Service-Token": "test-service-token"}


class StubEmbedder:
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[0.0, 1.0, 0.0] for _ in texts]


@pytest.fixture
def client_factory():
    def _make() -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    yield _make
    app.dependency_overrides.clear()


def write_audio(name: str = "m1/a.wav") -> str:
    from pathlib import Path

    path = Path(ai_settings.storage_root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF....WAVE")
    return name


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [{}, {"X-Service-Token": "wrong"}])
async def test_protected_routes_require_the_service_token(client_factory, headers) -> None:
    async with client_factory() as client:
        audio = await client.post("/audio/transcribe", headers=headers, json={"meeting_id": "m", "storage_key": "x"})
        rag = await client.post("/rag/summarize", headers=headers, json={"meeting_id": "m", "full_transcript": "t"})
    assert audio.status_code == 401 and rag.status_code == 401
    assert audio.json()["error"]["code"] == "INVALID_SERVICE_TOKEN"


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["../../etc/passwd", "/etc/passwd", "a/../../outside.wav", ""])
async def test_transcribe_rejects_keys_that_escape_the_storage_root(client_factory, key: str) -> None:
    """The local-file-read hole is closed: only files inside the storage root can be processed."""
    async with client_factory() as client:
        response = await client.post(
            "/audio/transcribe", headers=TOKEN, json={"meeting_id": "m", "storage_key": key}
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_STORAGE_KEY"


@pytest.mark.asyncio
async def test_transcribe_unknown_key_is_404(client_factory) -> None:
    async with client_factory() as client:
        response = await client.post(
            "/audio/transcribe", headers=TOKEN, json={"meeting_id": "m", "storage_key": "m1/missing.wav"}
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_transcribe_without_asr_key_returns_503_provider_not_configured(client_factory) -> None:
    key = write_audio()
    async with client_factory() as client:
        response = await client.post(
            "/audio/transcribe", headers=TOKEN, json={"meeting_id": "m", "storage_key": key}
        )
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "PROVIDER_NOT_CONFIGURED"
    assert error["message"] == "ASR provider not configured"


@pytest.mark.asyncio
async def test_transcribe_with_mock_engine_marks_result_as_demo(client_factory) -> None:
    app.dependency_overrides[get_audio_processor] = FakeAudioProcessor
    key = write_audio()
    async with client_factory() as client:
        response = await client.post(
            "/audio/transcribe", headers=TOKEN, json={"meeting_id": "m1", "storage_key": key}
        )
    body = response.json()
    assert response.status_code == 200
    assert body["is_demo"] is True
    assert body["segments_count"] == 2
    assert {"speaker", "start", "end", "text", "words"} <= set(body["segments"][0])


@pytest.mark.asyncio
async def test_summarize_without_llm_key_returns_503_not_a_canned_summary(client_factory) -> None:
    app.state.embedder = StubEmbedder()
    async with client_factory() as client:
        response = await client.post(
            "/rag/summarize", headers=TOKEN, json={"meeting_id": "m", "full_transcript": "A: hi"}
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_summarize_with_mock_engine_returns_structured_summary(client_factory) -> None:
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()
    async with client_factory() as client:
        response = await client.post(
            "/rag/summarize", headers=TOKEN, json={"meeting_id": "m", "full_transcript": "A: hi"}
        )
    body = response.json()
    assert response.status_code == 200
    assert body["executive_summary"] and body["key_points"] and body["action_items"]


@pytest.mark.asyncio
async def test_rag_query_returns_answer_with_citations(client_factory) -> None:
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()
    app.dependency_overrides[get_embedder] = lambda: StubEmbedder()
    segments = [
        {"segment_id": "s1", "speaker": "A", "start": 0.0, "end": 2.0, "text": "kế hoạch quý một"},
    ]
    async with client_factory() as client:
        response = await client.post(
            "/rag/query",
            headers=TOKEN,
            json={"meeting_id": "m", "query": "kế hoạch là gì", "segments": segments},
        )
    body = response.json()
    assert response.status_code == 200
    assert body["citations"][0]["segment_id"] == "s1"
