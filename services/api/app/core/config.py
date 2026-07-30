"""
Aegis AI — Application Configuration.

Centralizes all configuration using Pydantic Settings. Values are loaded from
environment variables and .env files, with type validation and sensible defaults.

Architecture Decision:
    We use a single Settings class with nested groupings rather than per-module
    settings objects. This makes configuration dependencies explicit and enables
    validation of cross-cutting concerns (e.g., database URL construction).
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "aegis-ai"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_version: str = "0.1.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "DEBUG"
    app_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    app_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("app_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── Database ─────────────────────────────────────────────────────────
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "aegis_ai"
    database_user: str = "aegis"
    database_password: str = "change-me"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    # ── Redis ────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ── Qdrant Vector DB ─────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "aegis_knowledge"

    # ── MinIO Object Storage ─────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "aegis-documents"
    minio_use_ssl: bool = False

    # ── AI Models ────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-large"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # Default LLM provider routing
    default_llm_provider: str = "openai"

    # ── Authentication ───────────────────────────────────────────────────
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # OAuth2 Providers
    oauth_google_client_id: str = ""
    oauth_google_client_secret: str = ""
    oauth_microsoft_client_id: str = ""
    oauth_microsoft_client_secret: str = ""

    # ── Rate Limiting ────────────────────────────────────────────────────
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # ── Integrations ─────────────────────────────────────────────────────
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_app_token: str = ""

    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""

    github_app_id: str = ""
    github_private_key_path: str = ""
    github_webhook_secret: str = ""

    # ── Vector Store ─────────────────────────────────────────────────────
    embedding_dimension: int = 3072
    similarity_threshold: float = 0.72

    # ── Observability ────────────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "aegis-ai-api"

    # ── Feature Flags ────────────────────────────────────────────────────
    feature_autonomous_mode: bool = False
    feature_multi_model: bool = True
    feature_streaming: bool = True

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings singleton.

    Using lru_cache ensures a single Settings instance is created and reused
    across the application lifecycle, avoiding repeated .env file parsing.
    """
    return Settings()
