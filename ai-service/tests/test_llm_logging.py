import io
import json

import httpx
import pytest
import structlog

from app.core.logging import configure_logging
from app.rag.llm_client import OpenAICompatibleLLMClient


@pytest.mark.asyncio
async def test_each_llm_call_logs_latency_and_token_usage() -> None:
    stream = io.StringIO()
    configure_logging(json_logs=True, stream=stream)
    try:

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "xin chào"}}],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 3},
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = OpenAICompatibleLLMClient(provider="gemini", api_key="k", client=http)
            assert await client.generate_chat_completion([{"role": "user", "content": "hi"}]) == "xin chào"

        entry = json.loads(stream.getvalue().splitlines()[-1])
        assert entry["event"] == "llm_call" and entry["provider"] == "gemini"
        assert (entry["prompt_tokens"], entry["completion_tokens"]) == (12, 3)
        assert entry["latency_ms"] >= 0
    finally:
        structlog.contextvars.clear_contextvars()
        configure_logging(json_logs=False)
