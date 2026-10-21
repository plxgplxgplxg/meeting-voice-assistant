from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Meeting Intelligence Backend API"
    environment: str = "development"
    debug: bool = True
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/meeting_intelligence"
    redis_url: str = "redis://localhost:6379/0"
    ai_service_url: str = "http://localhost:8001"


settings = Settings()
