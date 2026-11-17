import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

import httpx
import structlog

from app.core.errors import AIUnavailableError

logger = structlog.get_logger(__name__)

SUBMIT_TIMEOUT_SECONDS = 120.0
POLL_TIMEOUT_SECONDS = 30.0
SUMMARY_TIMEOUT_SECONDS = 120.0
EMBED_TIMEOUT_SECONDS = 60.0
ANSWER_TIMEOUT_SECONDS = 60.0
AGENT_TURN_TIMEOUT_SECONDS = 180.0
NON_RETRYABLE_CODES = frozenset({"PROVIDER_NOT_CONFIGURED", "INVALID_STORAGE_KEY", "AUDIO_NOT_FOUND"})

TranscriptionState = Literal["processing", "done", "error"]


@dataclass(frozen=True, slots=True)
class TranscriptionStatus:
    """State of one external transcription job.

    Attributes:
        status: ``processing`` while the provider works, ``done`` with segments, or ``error``.
        segments: Normalized transcript segments once done.
        is_demo: True when the AI service produced fixed mock data (development only).
        error: Provider error message when ``status`` is ``error``.
    """

    status: TranscriptionState
    segments: list[dict[str, Any]] = field(default_factory=list)
    is_demo: bool = False
    error: str | None = None


class AIServiceClient(Protocol):
    """Interface the backend uses to reach the stateless AI service."""

    async def submit_transcription(
        self, meeting_id: str, storage_key: str, language: str = "vi"
    ) -> str:
        """Start transcribing a stored recording.

        Args:
            meeting_id: Meeting the audio belongs to (for tracing).
            storage_key: Recording key relative to the storage root.
            language: Spoken language code.

        Returns:
            Provider job id to poll with :meth:`get_transcription`.
        """
        ...

    async def get_transcription(self, provider_job_id: str) -> TranscriptionStatus:
        """Fetch the current state of a transcription job.

        Args:
            provider_job_id: Id returned by :meth:`submit_transcription`.

        Returns:
            Current status with segments when finished.
        """
        ...

    async def summarize(self, meeting_id: str, transcript: str) -> dict[str, Any]:
        """Generate an executive summary, key points, and action items.

        Args:
            meeting_id: Meeting being summarized (for tracing).
            transcript: Full transcript text.

        Returns:
            Dict with ``executive_summary``, ``key_points`` and ``action_items``.
        """
        ...

    async def embed(self, texts: list[str], kind: Literal["passage", "query"]) -> list[list[float]]:
        """Compute embedding vectors.

        Args:
            texts: Texts to embed.
            kind: ``passage`` for indexed content, ``query`` for search queries.

        Returns:
            One vector per text.
        """
        ...

    async def rag_answer(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        chat_history: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Answer a question from already-retrieved chunks with citations.

        Args:
            query: User question.
            chunks: Retrieved transcript chunks.
            chat_history: Recent conversation turns.

        Returns:
            Tuple of answer text and citation dicts.
        """
        ...


class HttpAIServiceClient:
    """HTTP adapter for the AI service using a shared ``httpx.AsyncClient``."""

    def __init__(self, base_url: str, service_token: str, http_client: httpx.AsyncClient) -> None:
        """Initialize the adapter.

        Args:
            base_url: AI service origin.
            service_token: Shared secret sent as ``X-Service-Token``.
            http_client: Shared client owned by the application lifespan or worker runtime.
        """
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self.http = http_client

    async def submit_transcription(
        self, meeting_id: str, storage_key: str, language: str = "vi"
    ) -> str:
        data = await self._request(
            "POST",
            "/audio/transcribe",
            SUBMIT_TIMEOUT_SECONDS,
            {"meeting_id": meeting_id, "storage_key": storage_key, "language": language},
        )
        return str(data["provider_job_id"])

    async def get_transcription(self, provider_job_id: str) -> TranscriptionStatus:
        data = await self._request(
            "GET", f"/audio/transcribe/{provider_job_id}", POLL_TIMEOUT_SECONDS
        )
        return TranscriptionStatus(
            status=data["status"],
            segments=list(data.get("segments", [])),
            is_demo=bool(data.get("is_demo", False)),
            error=data.get("error"),
        )

    async def summarize(self, meeting_id: str, transcript: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/llm/summarize",
            SUMMARY_TIMEOUT_SECONDS,
            {"meeting_id": meeting_id, "full_transcript": transcript},
        )

    async def embed(self, texts: list[str], kind: Literal["passage", "query"]) -> list[list[float]]:
        data = await self._request(
            "POST", "/embeddings", EMBED_TIMEOUT_SECONDS, {"texts": texts, "kind": kind}
        )
        return [list(vector) for vector in data["vectors"]]

    async def rag_answer(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        chat_history: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, Any]]]:
        data = await self._request(
            "POST",
            "/rag/answer",
            ANSWER_TIMEOUT_SECONDS,
            {"query": query, "chunks": chunks, "chat_history": chat_history},
        )
        return str(data.get("answer", "")), list(data.get("citations", []))

    def _headers(self) -> dict[str, str]:
        headers = {"X-Service-Token": self.service_token}
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        if request_id:
            headers["X-Request-ID"] = str(request_id)
        return headers

    async def _request(
        self, method: str, path: str, timeout: float, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Call the AI service and map failures to ``AIUnavailableError``.

        Args:
            method: HTTP method.
            path: Route on the AI service.
            timeout: Per-request timeout in seconds.
            payload: Optional JSON body.

        Returns:
            Decoded JSON response body.

        Raises:
            AIUnavailableError: On transport failure or a non-200 response. Transport
                errors and upstream 5xx are marked retryable.
        """
        try:
            response = await self.http.request(
                method,
                f"{self.base_url}{path}",
                json=payload,
                headers=self._headers(),
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning("ai_service_unreachable", path=path, error=str(exc))
            raise AIUnavailableError("AI service is unreachable.", retryable=True) from exc

        if response.status_code != 200:
            message, code = self._parse_error(response)
            retryable = response.status_code >= 500 and code not in NON_RETRYABLE_CODES
            logger.warning(
                "ai_service_error", path=path, status_code=response.status_code, code=code
            )
            raise AIUnavailableError(message, retryable=retryable)
        return dict(response.json())

    @staticmethod
    def _parse_error(response: httpx.Response) -> tuple[str, str | None]:
        """Extract message and code from the AI service error envelope."""
        try:
            error = response.json()["error"]
            return str(error["message"]), error.get("code")
        except (ValueError, KeyError, TypeError):
            return f"AI service returned status {response.status_code}.", None


class AgentStreamClient(Protocol):
    """Interface for running one assistant turn on the AI service and streaming its events."""

    def stream_turn(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        """Run a turn and yield events as they arrive.

        Args:
            payload: Turn request: thread id, conversation id, meeting id, message,
                delegated token and the transcript revision the agent starts from.

        Returns:
            Async iterator of events ``{"type": ..., "data": {...}}`` where type is one of
            ``token``, ``tool_start``, ``tool_end``, ``proposal``, ``citation``, ``done``, ``error``.
        """
        ...


class HttpAgentStreamClient:
    """Streams assistant turns from the AI service over Server-Sent Events."""

    def __init__(self, base_url: str, service_token: str, http_client: httpx.AsyncClient) -> None:
        """Initialize the adapter.

        Args:
            base_url: AI service origin.
            service_token: Shared secret sent as ``X-Service-Token``.
            http_client: Shared client owned by the application lifespan.
        """
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self.http = http_client

    async def stream_turn(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        headers = {"X-Service-Token": self.service_token, "Accept": "text/event-stream"}
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        if request_id:
            headers["X-Request-ID"] = str(request_id)
        try:
            async with self.http.stream(
                "POST",
                f"{self.base_url}/agent/turn",
                json=payload,
                headers=headers,
                timeout=httpx.Timeout(AGENT_TURN_TIMEOUT_SECONDS, connect=10.0),
            ) as response:
                if response.status_code != 200:
                    raise AIUnavailableError(
                        f"AI service returned status {response.status_code}.",
                        retryable=response.status_code >= 500,
                    )
                event_type = "message"
                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line.removeprefix("event:").strip()
                    elif line.startswith("data:"):
                        yield {"type": event_type, "data": json.loads(line.removeprefix("data:"))}
                        event_type = "message"
        except httpx.HTTPError as exc:
            logger.warning("agent_stream_failed", error=str(exc))
            raise AIUnavailableError("AI service is unreachable.", retryable=True) from exc
