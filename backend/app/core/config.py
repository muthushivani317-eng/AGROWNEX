"""Application configuration (docs/BACKEND_ARCHITECTURE.md, docs/SECURITY.md).

All settings come from environment variables / `.env`. Secrets are never
hardcoded and never committed.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# The insecure default secret shipped for local dev. Production must override it;
# booting production with this value is refused (docs/SECURITY.md).
DEV_SESSION_SECRET = "dev-only-insecure-secret-change-me"


class ProductionConfigError(RuntimeError):
    """Raised when production is booted with an unsafe configuration."""


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
    # Connection pool sizing (docs/DEPLOYMENT.md → scaling).
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)
    db_pool_timeout: int = Field(default=30)

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
    session_secret: str = Field(default=DEV_SESSION_SECRET)

    # --- CORS ---
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # --- Docs exposure ---
    # In production, /docs and /openapi.json are disabled unless this is true.
    expose_docs: bool = Field(default=False)

    # --- Rate limiting (requests/minute per client) ---
    rate_limit_default: int = 100
    rate_limit_auth: int = 10
    rate_limit_window_seconds: int = 60
    # Reject request bodies larger than this before reading them into memory (8MB).
    max_request_body_bytes: int = 8 * 1024 * 1024

    # --- Per-farmer daily AI quota (protects the Gemini budget from abuse) ---
    ai_daily_disease_quota: int = 30
    ai_daily_chat_quota: int = 100

    # --- Mock-provider safety (product rule 5) ---
    # Production refuses to boot with a mock provider active unless allow-listed here.
    allow_mock_providers: bool = Field(default=False)

    # --- SMS / OTP delivery (MSG91) ---
    # "mock" (default; Firebase dispatches on-device) or "msg91" (server-side SMS).
    otp_provider: str = Field(default="mock")
    msg91_auth_key: str = Field(default="")
    msg91_sender_id: str = Field(default="AGROAI")
    msg91_template_id: str = Field(default="")
    msg91_base_url: str = Field(default="https://control.msg91.com/api/v5")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def validate_production(self) -> None:
        """Fail fast at boot on an unsafe production configuration (docs/SECURITY.md).

        Never let production start with wildcard CORS, the dev secret, or debug on —
        a farmer's data and the AI budget depend on these guards.
        """
        if not self.is_production:
            return
        problems: list[str] = []
        if self.session_secret == DEV_SESSION_SECRET:
            problems.append("SESSION_SECRET must be overridden (still the dev default).")
        if not self.cors_origins or "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must be an explicit list (no '*').")
        if self.debug:
            problems.append("DEBUG must be false in production.")
        if problems:
            raise ProductionConfigError(
                "Refusing to boot production: " + " ".join(problems)
            )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
