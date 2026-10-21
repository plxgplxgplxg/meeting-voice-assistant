from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """AI Service settings loaded from environment."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Meeting AI & Audio Service"
    whisper_model_size: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    huggingface_token: str = ""
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/meeting_intelligence"


ai_settings = AISettings()
