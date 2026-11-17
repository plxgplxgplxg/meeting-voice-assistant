from dataclasses import dataclass
from typing import Any, Protocol

import httpx
import structlog

from app.core.errors import AIUnavailableError

logger = structlog.get_logger(__name__)

AUDIO_TIMEOUT_SECONDS = 1860.0
SUMMARY_TIMEOUT_SECONDS = 120.0
QUERY_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class AudioTranscription:
    """Result of transcribing one recording.

    Attributes:
        segments: Normalized transcript segments.
        is_demo: True when the AI service produced fixed mock data (development only).
    """

    segments: list[dict[str, Any]]
    is_demo: bool = False


class AIServiceClient(Protocol):
    """Interface the backend uses to reach the stateless AI service."""

    async def transcribe(
        self, meeting_id: str, storage_key: str, language: str = "vi"
    ) -> AudioTranscription:
        """Transcribe and diarize a stored recording.

        Args:
            meeting_id: Meeting the audio belongs to (for tracing).
            storage_key: Storage key of the recording, relative to the storage root.
            language: Spoken language code.

        Returns:
            The transcript segments and whether they are demo data.
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

    async def rag_query(
        self,
        meeting_id: str,
        query: str,
        segments: list[dict[str, Any]],
        chat_history: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Answer a question from transcript segments with citations.

        Args:
            meeting_id: Meeting being queried.
            query: User question.
            segments: Candidate transcript segments.
            chat_history: Recent conversation turns.

        Returns:
            Tuple of answer text and citation dicts.
        """
        ...


class HttpAIServiceClient:
    """HTTP adapter for the AI service using a shared ``httpx.AsyncClient``."""

    def __init__(
        self,
        base_url: str,
        service_token: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        """Initialize the adapter.

        Args:
            base_url: AI service origin.
            service_token: Shared secret sent as ``X-Service-Token``.
            http_client: Shared client owned by the application lifespan.
        """
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self.http = http_client

    async def transcribe(
        self, meeting_id: str, storage_key: str, language: str = "vi"
    ) -> AudioTranscription:
        data = await self._post(
            "/audio/transcribe",
            {"meeting_id": meeting_id, "storage_key": storage_key, "language": language},
            AUDIO_TIMEOUT_SECONDS,
        )
        return AudioTranscription(
            segments=list(data.get("segments", [])), is_demo=bool(data.get("is_demo", False))
        )

    async def summarize(self, meeting_id: str, transcript: str) -> dict[str, Any]:
        return await self._post(
            "/rag/summarize",
            {"meeting_id": meeting_id, "full_transcript": transcript},
            SUMMARY_TIMEOUT_SECONDS,
        )

    async def rag_query(
        self,
        meeting_id: str,
        query: str,
        segments: list[dict[str, Any]],
        chat_history: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, Any]]]:
        data = await self._post(
            "/rag/query",
            {
                "meeting_id": meeting_id,
                "query": query,
                "segments": segments,
                "chat_history": chat_history,
            },
            QUERY_TIMEOUT_SECONDS,
        )
        return str(data.get("answer", "")), list(data.get("citations", []))

    async def _post(self, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        """POST JSON to the AI service and map failures to ``AIUnavailableError``.

        Args:
            path: Route on the AI service.
            payload: JSON body.
            timeout: Per-request timeout in seconds.

        Returns:
            Decoded JSON response body.

        Raises:
            AIUnavailableError: On transport failure or a non-200 response.
        """
        try:
            response = await self.http.post(
                f"{self.base_url}{path}",
                json=payload,
                headers={"X-Service-Token": self.service_token},
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning("ai_service_unreachable", path=path, error=str(exc))
            raise AIUnavailableError("AI service is unreachable.") from exc

        if response.status_code != 200:
            message = self._error_message(response)
            logger.warning(
                "ai_service_error", path=path, status_code=response.status_code, message=message
            )
            raise AIUnavailableError(message)
        return dict(response.json())

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        """Extract the AI service error message, falling back to the status code."""
        try:
            return str(response.json()["error"]["message"])
        except (ValueError, KeyError, TypeError):
            return f"AI service returned status {response.status_code}."
