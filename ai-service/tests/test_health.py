import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import ai_settings
from app.main import app


@pytest.mark.asyncio
async def test_health_reports_degraded_with_reasons_when_providers_are_missing() -> None:
    """Missing provider credentials are surfaced instead of reporting a false healthy state."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "degraded"
    assert "ASR provider not configured" in body["reasons"]
    assert "LLM provider not configured" in body["reasons"]


@pytest.mark.asyncio
async def test_health_is_healthy_when_everything_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai_settings, "gladia_api_key", "key")
    monkeypatch.setattr(ai_settings, "gemini_api_key", "key")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/health")).json()
    assert body == {"status": "healthy", "service": "ai-service", "reasons": []}
