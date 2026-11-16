from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """AI Service configuration settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Meeting AI & Audio Service"
    environment: str = "development"
    debug: bool = True

    # Audio Pipeline Configuration
    audio_pipeline_engine: str = "gladia"  # 'gladia' or 'mock'
    gladia_api_key: str = ""
    gladia_base_url: str = "https://api.gladia.io"

    # LLM & Generation Configuration
    llm_provider: str = "gemini"  # 'gemini' or 'openai'
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # Embedding & Vector Database
    embedding_model_name: str = "intfloat/multilingual-e5-small"
    device: str = "cpu"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/meeting_intelligence"
    redis_url: str = "redis://localhost:6379/0"

    # Legacy / Local fallback configurations
    whisper_model_size: str = "base"
    compute_type: str = "int8"
    huggingface_token: str = ""


ai_settings = AISettings()
