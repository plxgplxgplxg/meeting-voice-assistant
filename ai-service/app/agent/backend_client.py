from typing import Any, Protocol

import httpx
import structlog

logger = structlog.get_logger(__name__)

TOOL_TIMEOUT_SECONDS = 30.0


class BackendToolError(Exception):
    """A tool call was refused or failed on the backend.

    The message is safe to show to the model so it can explain the problem or adapt.

    Attributes:
        status: HTTP status returned by the backend.
        code: Backend error code, e.g. ``MEETING_FORBIDDEN`` or ``PLAN_FEATURE_REQUIRED``.
        message: Backend error message.
    """

    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class BackendToolClient(Protocol):
    """The backend operations available to the agent, always executed as the delegated user."""

    async def overview(self, meeting_id: str) -> dict[str, Any]:
        """Title, state, revision and per-speaker talk time."""
        ...

    async def search(self, meeting_id: str, query: str, k: int) -> list[dict[str, Any]]:
        """Hybrid search over the transcript."""
        ...

    async def read_segments(
        self,
        meeting_id: str,
        from_time: float | None,
        to_time: float | None,
        speaker: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Segments in a time window and/or of one speaker."""
        ...

    async def find_text(
        self, meeting_id: str, pattern: str, case_sensitive: bool
    ) -> list[dict[str, Any]]:
        """Segments containing a literal text."""
        ...

    async def get_summary(self, meeting_id: str) -> dict[str, Any]:
        """Summary, key points and action items."""
        ...

    async def propose(self, meeting_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """Store a proposed change; nothing is applied until the user approves."""
        ...

    async def create_artifact(self, meeting_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """Generate a document for the meeting."""
        ...


class HttpBackendToolClient:
    """HTTP adapter for ``/internal/agent/v1`` using the service token plus the delegated user token."""

    def __init__(
        self,
        base_url: str,
        service_token: str,
        delegated_token: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        """Initialize the adapter.

        Args:
            base_url: Backend origin.
            service_token: Shared secret proving the caller is the AI service.
            delegated_token: Short-lived token scoped to one meeting and one user.
            http_client: Shared HTTP client.
        """
        self.base = f"{base_url.rstrip('/')}/internal/agent/v1/meetings"
        self.service_token = service_token
        self.delegated_token = delegated_token
        self.http = http_client

    async def overview(self, meeting_id: str) -> dict[str, Any]:
        return await self._call("GET", f"{meeting_id}/overview")

    async def search(self, meeting_id: str, query: str, k: int) -> list[dict[str, Any]]:
        return await self._call("POST", f"{meeting_id}/search", {"query": query, "k": k})

    async def read_segments(
        self,
        meeting_id: str,
        from_time: float | None,
        to_time: float | None,
        speaker: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        params = {
            key: value
            for key, value in {
                "from_time": from_time,
                "to_time": to_time,
                "speaker": speaker,
                "limit": limit,
            }.items()
            if value is not None
        }
        return await self._call("GET", f"{meeting_id}/segments", params=params)

    async def find_text(
        self, meeting_id: str, pattern: str, case_sensitive: bool
    ) -> list[dict[str, Any]]:
        return await self._call(
            "POST", f"{meeting_id}/find", {"pattern": pattern, "case_sensitive": case_sensitive}
        )

    async def get_summary(self, meeting_id: str) -> dict[str, Any]:
        return await self._call("GET", f"{meeting_id}/summary")

    async def propose(self, meeting_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self._call("POST", f"{meeting_id}/agent-actions", body)

    async def create_artifact(self, meeting_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self._call("POST", f"{meeting_id}/artifacts", body)

    async def _call(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = await self.http.request(
            method,
            f"{self.base}/{path}",
            json=body,
            params=params,
            headers={
                "X-Service-Token": self.service_token,
                "Authorization": f"Bearer {self.delegated_token}",
            },
            timeout=TOOL_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            try:
                error = response.json()["error"]
                raise BackendToolError(response.status_code, error["code"], error["message"])
            except (ValueError, KeyError, TypeError):
                raise BackendToolError(
                    response.status_code, "BACKEND_ERROR", f"Backend returned {response.status_code}."
                ) from None
        return response.json()
