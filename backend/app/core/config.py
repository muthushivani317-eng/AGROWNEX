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
    public_api_url: str = Field(default="")
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "testserver"])
    request_timeout_seconds: float = Field(default=20.0, gt=0, le=120)

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
    firebase_auth_emulator_host: str = Field(default="")

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

    # --- Frozen disease classifier (Phase 3 Part 3) ---
    disease_model_required: bool = True
    disease_model_artifact_dir: str = "/models/mobilenetv3_small_v1"
    disease_max_image_bytes: int = 8 * 1024 * 1024
    disease_max_image_pixels: int = 25_000_000

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

    # --- Observability (Phase 4) ---
    sentry_dsn: str = Field(default="")
    # Structured JSON logs. Defaults to on in production, human-readable in dev.
    log_json: bool | None = Field(default=None)
    # Guards the /metrics endpoint; when empty, /metrics is closed (403).
    metrics_token: str = Field(default="")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def use_json_logs(self) -> bool:
        return self.is_production if self.log_json is None else self.log_json

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
        if not self.public_api_url.startswith("https://"):
            problems.append("PUBLIC_API_URL must be an HTTPS URL.")
        if any(
            marker in self.public_api_url.lower()
            for marker in ("localhost", "127.0.0.1", "10.0.2.2")
        ):
            problems.append("PUBLIC_API_URL must not target a local or emulator host.")
        if not self.trusted_hosts or "*" in self.trusted_hosts:
            problems.append("TRUSTED_HOSTS must be an explicit list (no '*').")
        if "localhost" in self.database_url or "localhost" in self.redis_url:
            problems.append("Production DATABASE_URL and REDIS_URL must not use localhost.")
        if not self.firebase_project_id or not self.firebase_credentials_json:
            problems.append("Firebase Admin credentials are required in production.")
        if self.firebase_auth_emulator_host:
            problems.append("Firebase Auth Emulator is forbidden in production.")
        if self.otp_provider == "mock":
            problems.append("OTP_PROVIDER=mock is forbidden in production.")
        if problems:
            raise ProductionConfigError(
                "Refusing to boot production: " + " ".join(problems)
            )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
