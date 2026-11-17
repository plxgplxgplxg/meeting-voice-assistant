import httpx
import pytest

from app.clients.ai_service_client import HttpAIServiceClient
from app.core.errors import AIUnavailableError


def make_client(handler) -> HttpAIServiceClient:
    transport = httpx.MockTransport(handler)
    return HttpAIServiceClient("http://ai", "secret-token", httpx.AsyncClient(transport=transport))


@pytest.mark.asyncio
async def test_client_sends_service_token_and_parses_transcription() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["token"] = request.headers["X-Service-Token"]
        seen["path"] = request.url.path
        return httpx.Response(200, json={"segments": [{"text": "hi"}], "is_demo": True})

    result = await make_client(handler).transcribe("m", "m/a.wav")
    assert seen == {"token": "secret-token", "path": "/audio/transcribe"}
    assert result.segments == [{"text": "hi"}] and result.is_demo is True


@pytest.mark.asyncio
async def test_error_envelope_message_is_preserved() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = {"error": {"code": "PROVIDER_NOT_CONFIGURED", "message": "ASR provider not configured"}}
        return httpx.Response(503, json=body)

    with pytest.raises(AIUnavailableError) as exc:
        await make_client(handler).transcribe("m", "m/a.wav")
    assert exc.value.message == "ASR provider not configured"
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_transport_failures_become_ai_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(AIUnavailableError):
        await make_client(handler).summarize("m", "text")
