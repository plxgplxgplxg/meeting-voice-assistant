import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import DEV_AI_SERVICE_TOKEN, DEV_SECRET_KEY, DEV_SEPAY_KEY, Settings

STRONG = "x" * 40


def production(**overrides: str) -> Settings:
    values = {
        "environment": "production",
        "secret_key": STRONG,
        "sepay_webhook_api_key": STRONG,
        "ai_service_token": STRONG,
        "cors_origins": "https://app.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_accepts_strong_secrets() -> None:
    settings = production()
    assert settings.is_production
    assert settings.cors_origins == ["https://app.example.com"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("secret_key", DEV_SECRET_KEY),
        ("sepay_webhook_api_key", DEV_SEPAY_KEY),
        ("ai_service_token", DEV_AI_SERVICE_TOKEN),
        ("secret_key", "short"),
    ],
)
def test_production_refuses_default_or_short_secrets(field: str, value: str) -> None:
    with pytest.raises(ValidationError) as exc:
        production(**{field: value})
    assert field.upper() in str(exc.value)


def test_production_refuses_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        production(cors_origins="*")


def test_development_keeps_defaults_and_parses_comma_separated_origins() -> None:
    settings = Settings(_env_file=None, cors_origins="http://a.test, http://b.test")
    assert settings.cors_origins == ["http://a.test", "http://b.test"]
    assert not settings.is_production


@pytest.mark.asyncio
async def test_error_envelope_carries_code_path_and_request_id(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me", headers={"X-Request-ID": "req-123"}
    )
    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "AUTHENTICATION_REQUIRED",
            "message": "Authentication required.",
            "path": "/api/v1/auth/me",
            "request_id": "req-123",
        }
    }
    assert response.headers["X-Request-ID"] == "req-123"


@pytest.mark.asyncio
async def test_validation_errors_use_the_same_envelope(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/login", json={"email": "nope"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_FAILED"
    assert "email" in error["message"]
