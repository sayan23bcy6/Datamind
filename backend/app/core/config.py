from functools import lru_cache
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DataMind"
    app_env: str = Field(default="development", alias="APP_ENV")
    secret_key: str = Field(default="dev-secret-key", alias="SECRET_KEY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(default="sqlite:///./datamind.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    storage_root: str = Field(default="./storage", alias="STORAGE_ROOT")

    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")
    embedding_model: str = Field(default="gemini-embedding-001", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=768, alias="EMBEDDING_DIMENSION")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")

    max_iterations: int = Field(default=3, alias="MAX_ITERATIONS")
    cost_budget_tokens: int = Field(default=200000, alias="COST_BUDGET_TOKENS")
    cost_budget_tool_calls: int = Field(default=500, alias="COST_BUDGET_TOOL_CALLS")

    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")
    vite_api_url: str = Field(default="http://localhost:8000", alias="VITE_API_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def validate_llm_provider_credentials(self) -> "Settings":
        if self.llm_provider and self.llm_provider.strip().lower() == "gemini":
            if not self.google_api_key or not self.google_api_key.strip():
                raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER is configured to 'gemini'")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
