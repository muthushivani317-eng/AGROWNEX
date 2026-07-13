"""Application configuration (docs/BACKEND_ARCHITECTURE.md, docs/SECURITY.md).

All settings come from environment variables / `.env`. Secrets are never
hardcoded and never committed.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "AgrowAI API"
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    api_v1_prefix: str = "/api/v1"

    # --- Database (PostgreSQL + PostGIS) ---
    database_url: str = Field(
        default="postgresql+asyncpg://agrowai:agrowai@localhost:5432/agrowai",
    )
    db_echo: bool = Field(default=False)

    # --- Cache / broker ---
    redis_url: str = Field(default="redis://localhost:6379/0")
    # Response cache backend for idempotent reads (weather/market): "memory" (default,
    # process-local) or "redis" (shared across workers). Diagnoses/chat are never cached.
    cache_backend: str = Field(default="memory")

    # --- Auth (Firebase) ---
    firebase_project_id: str = Field(default="")
    firebase_credentials_json: str = Field(default="")

    # Server-side pepper for hashing refresh tokens / OTP fingerprints. MUST be
    # overridden in production via env; never commit a real secret.
    session_secret: str = Field(default="dev-only-insecure-secret-change-me")

    # --- CORS ---
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # --- Rate limiting (requests/minute) ---
    rate_limit_default: int = 100
    rate_limit_auth: int = 10

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
