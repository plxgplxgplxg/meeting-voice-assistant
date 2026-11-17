import httpx
import pytest

from app.clients.ai_service_client import HttpAIServiceClient
from app.core.errors import AIUnavailableError


def make_client(handler) -> HttpAIServiceClient:
    transport = httpx.MockTransport(handler)
    return HttpAIServiceClient("http://ai", "secret-token", httpx.AsyncClient(transport=transport))


@pytest.mark.asyncio
async def test_submit_and_poll_use_the_async_contract_and_send_the_service_token() -> None:
    seen: list[tuple[str, str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.headers["X-Service-Token"]))
        if request.method == "POST":
            return httpx.Response(200, json={"provider_job_id": "job-9", "status": "submitted"})
        return httpx.Response(200, json={"status": "done", "segments": [{"text": "hi"}], "is_demo": True})

    client = make_client(handler)
    job_id = await client.submit_transcription("m", "m/a.wav")
    result = await client.get_transcription(job_id)

    assert seen == [
        ("POST", "/audio/transcribe", "secret-token"),
        ("GET", "/audio/transcribe/job-9", "secret-token"),
    ]
    assert result.status == "done" and result.segments == [{"text": "hi"}] and result.is_demo


@pytest.mark.asyncio
async def test_embed_and_rag_answer_payloads() -> None:
    bodies: dict[str, dict] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        bodies[request.url.path] = json.loads(request.content)
        if request.url.path == "/embeddings":
            return httpx.Response(200, json={"vectors": [[0.1, 0.2]], "model": "m", "dimensions": 2})
        return httpx.Response(200, json={"answer": "a [S01]", "citations": [{"segment_id": "s"}]})

    client = make_client(handler)
    assert await client.embed(["x"], "query") == [[0.1, 0.2]]
    answer, citations = await client.rag_answer("q", [{"text": "t"}], [])

    assert bodies["/embeddings"] == {"texts": ["x"], "kind": "query"}
    assert bodies["/rag/answer"]["chunks"] == [{"text": "t"}]
    assert answer == "a [S01]" and citations == [{"segment_id": "s"}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "code", "retryable"),
    [
        (503, "PROVIDER_NOT_CONFIGURED", False),
        (502, "PROVIDER_ERROR", True),
        (500, None, True),
        (400, "INVALID_STORAGE_KEY", False),
        (404, "AUDIO_NOT_FOUND", False),
    ],
)
async def test_error_envelope_is_preserved_and_classified_as_retryable_or_not(status, code, retryable) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = {"error": {"code": code, "message": "provider says no"}} if code else {"oops": 1}
        return httpx.Response(status, json=body)

    with pytest.raises(AIUnavailableError) as exc:
        await make_client(handler).submit_transcription("m", "k")
    assert exc.value.retryable is retryable
    if code:
        assert exc.value.message == "provider says no"


@pytest.mark.asyncio
async def test_transport_failures_are_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(AIUnavailableError) as exc:
        await make_client(handler).summarize("m", "text")
    assert exc.value.retryable is True


@pytest.mark.asyncio
async def test_request_id_is_forwarded_when_bound() -> None:
    import structlog

    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, json={"vectors": [[1.0]], "model": "m", "dimensions": 1})

    structlog.contextvars.bind_contextvars(request_id="req-77")
    try:
        await make_client(handler).embed(["x"], "passage")
    finally:
        structlog.contextvars.clear_contextvars()
    assert seen["x-request-id"] == "req-77"
