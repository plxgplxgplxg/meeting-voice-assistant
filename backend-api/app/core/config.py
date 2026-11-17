from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEV_SECRET_KEY = "development-only-secret-key-change-before-deploy"
DEV_SEPAY_KEY = "development-only-sepay-key"
DEV_AI_SERVICE_TOKEN = "development-only-ai-service-token"
MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Meeting Intelligence Backend API"
    environment: str = "development"
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/meeting_intelligence"
    redis_url: str = "redis://localhost:6379/0"
    ai_service_url: str = "http://localhost:8001"
    ai_service_token: str = DEV_AI_SERVICE_TOKEN

    # Comma separated list in the environment, e.g. "https://a.com,https://b.com"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Security & Auth
    secret_key: str = DEV_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    bcrypt_rounds: int = 12
    refresh_token_expire_days: int = 30

    # Storage
    storage_root: str = "/tmp/meeting_storage"
    max_upload_mb: int = 500

    # Background processing
    transcription_poll_seconds: float = 5.0
    transcription_max_wait_seconds: int = 1800
    job_max_attempts: int = 3
    job_retry_base_seconds: float = 10.0

    # VietQR / SePay Configuration
    sepay_bank_code: str = "MBBank"
    sepay_account_number: str = "0987654321"
    sepay_account_name: str = "DEMO ACCOUNT HOLDER"
    sepay_webhook_api_key: str = DEV_SEPAY_KEY

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        """Accept a comma separated string for the CORS origin list.

        Args:
            value: Raw value from the environment or constructor.

        Returns:
            A list of trimmed origins when a string was given, else the input.
        """
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        """Whether the process runs with production safeguards enabled."""
        return self.environment.lower() == "production"

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        """Refuse to start in production with default or weak secrets.

        Returns:
            The validated settings instance.

        Raises:
            ValueError: If a secret equals its development default or is too short.
        """
        if not self.is_production:
            return self

        secrets_to_check = {
            "SECRET_KEY": (self.secret_key, DEV_SECRET_KEY),
            "SEPAY_WEBHOOK_API_KEY": (self.sepay_webhook_api_key, DEV_SEPAY_KEY),
            "AI_SERVICE_TOKEN": (self.ai_service_token, DEV_AI_SERVICE_TOKEN),
        }
        problems = [
            name
            for name, (value, default) in secrets_to_check.items()
            if value == default or len(value) < MIN_PRODUCTION_SECRET_LENGTH
        ]
        if problems:
            raise ValueError(
                "Refusing to start in production: "
                f"{', '.join(problems)} must be set to a non-default value of at "
                f"least {MIN_PRODUCTION_SECRET_LENGTH} characters."
            )
        if "*" in self.cors_origins:
            raise ValueError("Refusing to start in production with wildcard CORS_ORIGINS.")
        return self


settings = Settings()
