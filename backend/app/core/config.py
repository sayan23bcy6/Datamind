from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DataMind"
    app_env: str = "development"
    secret_key: str = Field(default="dev-secret-key", alias="SECRET_KEY")
    database_url: str = Field(default="sqlite:///./datamind.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    storage_root: str = Field(default="./storage", alias="STORAGE_ROOT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    postgres_user: str = "datamind_user"
    postgres_password: str = "change-me"
    postgres_db: str = "datamind"
    google_api_key: str = "replace-me-local-only"
    llm_provider: str = "mock"
    gemini_model: str = "gemini-2.0-flash"
    vite_api_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
