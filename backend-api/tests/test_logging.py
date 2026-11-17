import io
import json

import pytest
import structlog
from httpx import AsyncClient

from app.api.deps import CurrentUser
from app.core.logging import configure_logging
from app.main import app as fastapi_app
from tests.conftest import RegisterUser


@pytest.fixture
def log_stream():
    stream = io.StringIO()
    configure_logging(json_logs=True, stream=stream)
    yield stream
    structlog.contextvars.clear_contextvars()
    configure_logging(json_logs=False)


def lines(stream: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_json_logs_carry_bound_request_and_user_ids(log_stream) -> None:
    structlog.contextvars.bind_contextvars(request_id="req-1", user_id="user-1")
    structlog.get_logger("test").info("something_happened", detail="x")

    (entry,) = lines(log_stream)
    assert entry["event"] == "something_happened" and entry["level"] == "info"
    assert (entry["request_id"], entry["user_id"], entry["detail"]) == ("req-1", "user-1", "x")
    assert "timestamp" in entry


@pytest.mark.asyncio
async def test_request_id_and_user_id_reach_logs_emitted_while_handling_a_request(
    client: AsyncClient, register_user: RegisterUser, log_stream
) -> None:
    """The middleware binds request_id and the auth dependency binds user_id for the whole request."""

    async def probe(user: CurrentUser) -> dict[str, str]:
        structlog.get_logger("probe").info("probe_called")
        return {"user": str(user.id)}

    account = await register_user("logs@example.com")
    log_stream.truncate(0)
    log_stream.seek(0)
    fastapi_app.add_api_route("/__probe", probe)
    try:
        response = await client.get(
            "/__probe", headers={**account.headers, "X-Request-ID": "trace-9"}
        )
    finally:
        fastapi_app.router.routes.pop()

    assert response.status_code == 200 and response.headers["X-Request-ID"] == "trace-9"
    entry = next(e for e in lines(log_stream) if e["event"] == "probe_called")
    assert entry["request_id"] == "trace-9" and entry["user_id"] == str(account.id)
