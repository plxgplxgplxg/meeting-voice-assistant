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

    # Security & Auth
    secret_key: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Storage
    storage_root: str = "/tmp/meeting_storage"

    # VietQR / SePay Configuration
    sepay_bank_code: str = "MBBank"
    sepay_account_number: str = "0987654321"
    sepay_account_name: str = "NGUYEN PHUONG LINH"
    sepay_webhook_api_key: str = "sepay_secret_key_demo"


settings = Settings()
