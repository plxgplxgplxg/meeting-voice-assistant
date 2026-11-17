import json
from collections.abc import AsyncIterator, Callable
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.backend_client import BackendToolClient, HttpBackendToolClient
from app.agent.runner import AgentTurnRequest, AgentTurnRunner
from app.core.auth import require_service_token
from app.core.config import ai_settings
from app.core.errors import ProviderNotConfiguredError

router = APIRouter(tags=["Agent"], dependencies=[Depends(require_service_token)])

THREAD_ID_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"
UUID_PATTERN = r"^[0-9a-fA-F-]{36}$"
SSE_HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}


class AgentTurnBody(BaseModel):
    """One assistant turn requested by the backend."""

    thread_id: str = Field(pattern=THREAD_ID_PATTERN)
    conversation_id: str = Field(pattern=UUID_PATTERN)
    meeting_id: str = Field(pattern=UUID_PATTERN)
    message: str = Field(min_length=1, max_length=4000)
    delegated_token: str = Field(min_length=20, max_length=4000)
    base_revision: int = Field(ge=0)


def get_agent_runner(request: Request) -> AgentTurnRunner:
    """Provide the turn runner created at startup.

    Raises:
        ProviderNotConfiguredError: If the LLM provider was not configured at startup.
    """
    runner: AgentTurnRunner | None = getattr(request.app.state, "agent_runner", None)
    if runner is None:
        raise ProviderNotConfiguredError(
            getattr(request.app.state, "agent_error", None) or "Assistant is not available."
        )
    return runner


def get_backend_client_factory(request: Request) -> Callable[[str], BackendToolClient]:
    """Provide a factory building a backend tool client for a delegated token."""

    def build(delegated_token: str) -> BackendToolClient:
        http: httpx.AsyncClient = request.app.state.http
        return HttpBackendToolClient(
            ai_settings.backend_api_url, ai_settings.ai_service_token, delegated_token, http
        )

    return build


def encode(event: dict) -> str:
    """Format one runner event as an SSE frame."""
    return f"event: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"


@router.post("/agent/turn")
async def agent_turn(
    body: AgentTurnBody,
    runner: Annotated[AgentTurnRunner, Depends(get_agent_runner)],
    backend_factory: Annotated[
        Callable[[str], BackendToolClient], Depends(get_backend_client_factory)
    ],
) -> StreamingResponse:
    """Run one assistant turn and stream ``token``, ``tool_start``, ``tool_end``, ``proposal``,
    ``citation``, ``done`` and ``error`` events.

    The delegated token is passed straight to the backend client. It is never placed in
    model-visible state.
    """
    backend = backend_factory(body.delegated_token)
    request = AgentTurnRequest(
        thread_id=body.thread_id,
        conversation_id=body.conversation_id,
        meeting_id=body.meeting_id,
        message=body.message,
        base_revision=body.base_revision,
    )

    async def stream() -> AsyncIterator[str]:
        async for event in runner.run(request, backend):
            yield encode(event)

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)

