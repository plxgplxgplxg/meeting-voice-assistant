import pytest

from app.core.config import ai_settings


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Give every test a clean environment: no provider keys and a temporary storage root."""
    monkeypatch.setattr(ai_settings, "gladia_api_key", "")
    monkeypatch.setattr(ai_settings, "gemini_api_key", "")
    monkeypatch.setattr(ai_settings, "openai_api_key", "")
    monkeypatch.setattr(ai_settings, "audio_pipeline_engine", "gladia")
    monkeypatch.setattr(ai_settings, "environment", "development")
    monkeypatch.setattr(ai_settings, "storage_root", str(tmp_path / "storage"))
    monkeypatch.setattr(ai_settings, "ai_service_token", "test-service-token")
    (tmp_path / "storage").mkdir()
