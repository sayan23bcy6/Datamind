from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DataMind"
    app_env: str = "development"
    secret_key: str = "dev-secret-key"
    database_url: str = "sqlite:///./datamind.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: str = "./storage"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
