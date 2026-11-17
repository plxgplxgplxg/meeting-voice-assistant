import json
import os
import uuid

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

from app.agent.backend_client import BackendToolError, HttpBackendToolClient
from app.agent.fake import FakeAgentChatModel
from app.agent.graph import build_graph
from app.agent.llm import build_chat_model
from app.agent.runner import AgentTurnRunner
from app.agent.tools import ALL_TOOLS
from app.core.config import ai_settings
from app.core.errors import ProviderNotConfiguredError
from app.main import app
from app.routers.agent import get_agent_runner, get_backend_client_factory
from tests.agent_fakes import FakeBackend, ScriptedChatModel, tool_call_message

TOKEN = {"X-Service-Token": "test-service-token"}
BODY = {
    "thread_id": "thread-12345678",
    "conversation_id": str(uuid.uuid4()),
    "meeting_id": str(uuid.uuid4()),
    "message": "Tóm tắt cuộc họp",
    "delegated_token": "d" * 40,
    "base_revision": 2,
}


@pytest.fixture
def client_factory():
    def _make() -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    yield _make
    app.dependency_overrides.clear()
    for name in ("agent_runner", "agent_error"):
        if hasattr(app.state, name):
            delattr(app.state, name)


def sse_events(text: str) -> list[tuple[str, dict]]:
    events = []
    for frame in text.strip().split("\n\n"):
        event_line, data_line = frame.splitlines()[:2]
        events.append((event_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: "))))
    return events


@pytest.mark.asyncio
async def test_agent_turn_requires_the_service_token(client_factory) -> None:
    async with client_factory() as client:
        missing = await client.post("/agent/turn", json=BODY)
        wrong = await client.post("/agent/turn", headers={"X-Service-Token": "nope"}, json=BODY)
    assert (missing.status_code, wrong.status_code) == (401, 401)


@pytest.mark.asyncio
async def test_agent_turn_is_unavailable_without_a_configured_llm(client_factory) -> None:
    app.state.agent_runner = None
    app.state.agent_error = "LLM provider not configured: gemini"
    async with client_factory() as client:
        response = await client.post("/agent/turn", headers=TOKEN, json=BODY)
    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "PROVIDER_NOT_CONFIGURED",
        "message": "LLM provider not configured: gemini",
        "path": "/agent/turn",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override",
    [{"thread_id": "../etc"}, {"meeting_id": "not-a-uuid"}, {"message": ""}, {"delegated_token": "short"}, {"base_revision": -1}],
)
async def test_agent_turn_validates_its_input(client_factory, override) -> None:
    model = ScriptedChatModel(replies=[AIMessage(content="x")], seen=[])
    app.dependency_overrides[get_agent_runner] = lambda: AgentTurnRunner(
        build_graph(model, ALL_TOOLS, InMemorySaver()), 8
    )
    async with client_factory() as client:
        response = await client.post("/agent/turn", headers=TOKEN, json={**BODY, **override})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agent_turn_streams_sse_events_and_hands_the_token_only_to_the_backend_client(
    client_factory,
) -> None:
    backend = FakeBackend()
    tokens_given: list[str] = []
    model = ScriptedChatModel(
        replies=[tool_call_message(("get_meeting_overview", {})), AIMessage(content="Họp về kiến trúc.")],
        seen=[],
    )
    runner = AgentTurnRunner(build_graph(model, ALL_TOOLS, InMemorySaver()), recursion_limit=8)

    def factory(delegated_token: str):
        tokens_given.append(delegated_token)
        return backend

    app.dependency_overrides[get_agent_runner] = lambda: runner
    app.dependency_overrides[get_backend_client_factory] = lambda: factory
    async with client_factory() as client:
        response = await client.post("/agent/turn", headers=TOKEN, json=BODY)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = sse_events(response.text)
    assert [e for e, _ in events][:2] == ["tool_start", "tool_end"] and events[-1][0] == "done"
    assert tokens_given == [BODY["delegated_token"]]
    assert BODY["delegated_token"] not in response.text
    assert BODY["delegated_token"] not in json.dumps([[str(m.content) for m in turn] for turn in model.seen])


@pytest.mark.asyncio
async def test_http_backend_client_sends_both_credentials_and_maps_errors() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/summary"):
            return httpx.Response(402, json={"error": {"code": "PLAN_FEATURE_REQUIRED", "message": "Upgrade."}})
        if request.url.path.endswith("/overview"):
            return httpx.Response(502, text="bad gateway")
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        backend = HttpBackendToolClient("http://backend:8000", "svc-token", "delegated", http)
        await backend.read_segments("m1", 5.0, None, "Speaker 1", 20)
        await backend.find_text("m1", "Gemany", True)
        with pytest.raises(BackendToolError) as refused:
            await backend.get_summary("m1")
        with pytest.raises(BackendToolError) as broken:
            await backend.overview("m1")

    segments, find = seen[0], seen[1]
    assert segments.url.path == "/internal/agent/v1/meetings/m1/segments"
    assert dict(segments.url.params) == {"from_time": "5.0", "speaker": "Speaker 1", "limit": "20"}
    assert segments.headers["X-Service-Token"] == "svc-token"
    assert segments.headers["Authorization"] == "Bearer delegated"
    assert json.loads(find.content) == {"pattern": "Gemany", "case_sensitive": True}
    assert (refused.value.status, refused.value.code) == (402, "PLAN_FEATURE_REQUIRED")
    assert (broken.value.status, broken.value.code) == (502, "BACKEND_ERROR")


def test_chat_model_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ProviderNotConfiguredError):
        build_chat_model()

    monkeypatch.setattr(ai_settings, "gemini_api_key", "key")
    gemini = build_chat_model()
    assert gemini.model_name == "gemini-2.0-flash"
    assert "generativelanguage.googleapis.com" in str(gemini.openai_api_base)
    assert isinstance(gemini.openai_api_key, SecretStr)

    monkeypatch.setattr(ai_settings, "llm_provider", "openai")
    monkeypatch.setattr(ai_settings, "openai_api_key", "key")
    assert build_chat_model().model_name == "gpt-4o-mini"

    monkeypatch.setattr(ai_settings, "audio_pipeline_engine", "mock")
    assert isinstance(build_chat_model(), FakeAgentChatModel)
    monkeypatch.setattr(ai_settings, "environment", "production")
    assert not isinstance(build_chat_model(), FakeAgentChatModel)


@pytest.mark.skipif(not os.environ.get("AGENT_TEST_PG_URL"), reason="set AGENT_TEST_PG_URL for PostgreSQL checkpoints")
@pytest.mark.asyncio
async def test_postgres_checkpointer_persists_conversations_in_its_own_schema() -> None:
    import psycopg

    from app.agent.checkpoint import open_checkpointer
    from tests.agent_fakes import FakeBackend as Backend

    url = os.environ["AGENT_TEST_PG_URL"]
    thread = f"thread-{uuid.uuid4().hex[:12]}"

    async def run_turn(saver, message: str, model: ScriptedChatModel) -> None:
        runner = AgentTurnRunner(build_graph(model, ALL_TOOLS, saver), 8)
        from app.agent.runner import AgentTurnRequest

        req = AgentTurnRequest(thread, str(uuid.uuid4()), str(uuid.uuid4()), message, 0)
        async for _ in runner.run(req, Backend()):
            pass

    first = ScriptedChatModel(replies=[AIMessage(content="Một.")], seen=[])
    async with open_checkpointer(url) as saver:
        await run_turn(saver, "câu một", first)

    second = ScriptedChatModel(replies=[AIMessage(content="Hai.")], seen=[])
    async with open_checkpointer(url) as saver:
        await run_turn(saver, "câu hai", second)

    assert any("câu một" in str(m.content) for m in second.seen[0]), "history survived a new connection pool"
    async with await psycopg.AsyncConnection.connect(url, autocommit=True) as connection:
        rows = await (await connection.execute(
            "SELECT table_schema FROM information_schema.tables WHERE table_name = 'checkpoints'"
        )).fetchall()
    assert [r[0] for r in rows] == ["langgraph"]
