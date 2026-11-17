from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_AI_SERVICE_TOKEN = "development-only-ai-service-token"
MIN_PRODUCTION_SECRET_LENGTH = 32


class AISettings(BaseSettings):
    """AI Service configuration settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Meeting AI & Audio Service"
    environment: str = "development"
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")

    # Shared secret the backend sends as X-Service-Token
    ai_service_token: str = DEV_AI_SERVICE_TOKEN

    # Root directory that audio storage keys are resolved under
    storage_root: str = "/tmp/meeting_storage"

    # Audio Pipeline Configuration
    audio_pipeline_engine: str = "gladia"  # 'gladia', or 'mock' (development only)
    gladia_api_key: str = ""
    gladia_base_url: str = "https://api.gladia.io"
    gladia_max_wait_seconds: int = 1800

    # LLM & Generation Configuration
    llm_provider: str = "gemini"  # 'gemini' or 'openai'
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # Agent
    backend_api_url: str = "http://backend-api:8000"
    # ai-service-private conversation state (LangGraph checkpoints) in its own schema. Never business data.
    agent_checkpoint_db_url: str = ""
    agent_recursion_limit: int = 8

    # Embedding & Vector Database
    embedding_model_name: str = "intfloat/multilingual-e5-small"
    device: str = "cpu"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/meeting_intelligence"
    redis_url: str = "redis://localhost:6379/0"

    # Legacy / Local fallback configurations
    whisper_model_size: str = "base"
    compute_type: str = "int8"
    huggingface_token: str = ""

    @property
    def llm_api_key(self) -> str:
        """API key of the selected LLM provider."""
        return self.gemini_api_key if self.llm_provider.lower() == "gemini" else self.openai_api_key

    @property
    def llm_model_name(self) -> str:
        """Default chat model of the selected LLM provider."""
        return "gemini-2.0-flash" if self.llm_provider.lower() == "gemini" else "gpt-4o-mini"

    @property
    def llm_base_url(self) -> str | None:
        """OpenAI-compatible base URL for Gemini, or None to use OpenAI's default."""
        if self.llm_provider.lower() == "gemini":
            return "https://generativelanguage.googleapis.com/v1beta/openai/"
        return None

    @property
    def is_production(self) -> bool:
        """Whether the process runs with production safeguards enabled."""
        return self.environment.lower() == "production"

    @property
    def use_mock_engine(self) -> bool:
        """Whether fake ASR and LLM adapters are selected (development only)."""
        return self.audio_pipeline_engine == "mock"

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        """Refuse to start in production with the default token or the mock engine.

        Returns:
            The validated settings instance.

        Raises:
            ValueError: If production is configured insecurely.
        """
        if not self.is_production:
            return self
        if (
            self.ai_service_token == DEV_AI_SERVICE_TOKEN
            or len(self.ai_service_token) < MIN_PRODUCTION_SECRET_LENGTH
        ):
            raise ValueError(
                "Refusing to start in production: AI_SERVICE_TOKEN must be a non-default "
                f"value of at least {MIN_PRODUCTION_SECRET_LENGTH} characters."
            )
        if self.use_mock_engine:
            raise ValueError("Refusing to start in production with AUDIO_PIPELINE_ENGINE=mock.")
        return self


ai_settings = AISettings()
