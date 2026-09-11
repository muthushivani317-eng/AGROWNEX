"""Application configuration (docs/BACKEND_ARCHITECTURE.md, docs/SECURITY.md).

All settings come from environment variables / `.env`. Secrets are never
hardcoded and never committed.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# The insecure default secret shipped for local dev. Production must override it;
# booting production with this value is refused (docs/SECURITY.md).
DEV_SESSION_SECRET = "dev-only-insecure-secret-change-me"


def normalize_async_database_url(url: str) -> str:
    """Return an asyncpg URL for plain PostgreSQL schemes.

    Railway supplies a standard PostgreSQL URL. The application and Alembic
    both use SQLAlchemy's async engine, so only that URL's scheme needs to be
    adapted. Everything after the scheme, including credentials and query
    parameters, is preserved verbatim.
    """
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    return url


class ProductionConfigError(RuntimeError):
    """Raised when production is booted with an unsafe configuration."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "AgrowAI API"
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("environment", "APP_ENV"),
    )
    debug: bool = Field(default=True)
    organic_trusted_weather_enabled: bool = Field(default=True)
    # Two-release private-photo rollout. Keep false until the authenticated-image
    # mobile release is installed and legacy objects have been copied/verified.
    private_disease_images_enabled: bool = Field(default=False)
    api_v1_prefix: str = "/api/v1"
    public_api_url: str = Field(default="")
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "testserver"])
    request_timeout_seconds: float = Field(default=20.0, gt=0, le=120)

    # --- Database (PostgreSQL + PostGIS) ---
    database_url: str = Field(
        default="postgresql+asyncpg://agrowai:agrowai@localhost:5432/agrowai",
    )
    migration_database_url: str | None = Field(default=None)
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

    # Separate Admin Web/PWA session. The cookie carries a Firebase session
    # cookie and is never readable by browser JavaScript.
    admin_web_origins: list[str] = Field(default_factory=list)
    admin_session_cookie_name: str = "agrowai_admin_session"
    admin_session_ttl_hours: int = Field(default=8, ge=1, le=24 * 14)
    admin_require_mfa: bool = False
    # Optional single-owner lockdown. Empty retains normal team RBAC.
    admin_owner_firebase_uid: str = Field(default="", max_length=128, pattern=r"^\S*$")
    admin_sensitive_reauth_minutes: int = Field(default=15, ge=5, le=60)

    # --- Admin cloud billing visibility (BigQuery Cloud Billing export) ---
    # Fully-qualified export table: project.dataset.gcp_billing_export_v1_XXXXXX.
    # Empty means the dashboard reports "not configured" rather than estimating.
    gcp_billing_project_id: str = Field(default="")
    gcp_billing_export_table: str = Field(default="")
    gcp_billing_query_project_id: str = Field(default="")
    gcp_billing_location: str = Field(default="US")
    gcp_billing_budget_inr: float = Field(default=2000.0, gt=0)

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
    # X-Forwarded-For is client-supplied and trivially spoofable unless a trusted
    # edge proxy (load balancer/CDN) overwrites it before the request reaches us.
    # Defaults to false (trust the direct TCP peer only) so a bare deployment
    # can't have its rate limits/audit IPs bypassed by a forged header; set true
    # only when deployed behind a proxy that is known to sanitize this header
    # (docs/SECURITY.md → client IP resolution).
    trust_proxy_headers: bool = Field(default=False)

    # --- Frozen disease classifier (Phase 3 Part 3) ---
    disease_model_required: bool = True
    disease_model_artifact_dir: str = "/models/mobilenetv3_small_v1"
    disease_max_image_bytes: int = 8 * 1024 * 1024
    disease_max_image_pixels: int = 25_000_000

    # --- Per-farmer daily AI quota (protects the Gemini budget from abuse) ---
    ai_daily_disease_quota: int = Field(default=5, ge=1)
    ai_daily_chat_quota: int = Field(default=10, ge=1)
    ai_daily_plant_identifier_quota: int = 15
    ai_daily_growth_quota: int = 10
    ai_daily_nutrient_quota: int = 10

    # --- Controlled OpenAI disease shadow evaluation ---
    # Disabled by default. This never changes or appears in the farmer response.
    openai_disease_comparison_enabled: bool = False
    openai_disease_comparison_api_key: str = ""
    openai_disease_comparison_model: str = ""
    openai_disease_comparison_timeout_seconds: float = Field(default=30.0, gt=0, le=120)

    # --- Farmer-facing AI vision diagnosis (general release) ---
    # Primary diagnosis engine for crops with no field-validated local classifier,
    # and an independent read alongside banana/chilli/redgram's local models
    # (which are public-dataset provisional models, not farmer-photo validated —
    # see model_artifacts/frozen_runtime/*/README.md). Distinct from the
    # internal-only shadow comparison above: this one is shown to the farmer.
    openai_vision_diagnosis_api_key: str = ""
    openai_vision_diagnosis_model: str = "gpt-4o"
    openai_vision_diagnosis_timeout_seconds: float = Field(default=45.0, gt=0, le=120)

    # --- Mock-provider safety (product rule 5) ---
    # Production refuses to boot with a mock provider active unless allow-listed here.
    allow_mock_providers: bool = Field(default=False)

    # --- Legacy-joint supervised field testing ---
    # Permission alone never activates inference. A ControlledTester must also
    # activate a process-local session, which intentionally resets on restart.
    legacy_joint_field_test_override_permitted: bool = Field(default=False)
    legacy_joint_field_test_audit_path: str = Field(
        default="logs/field_testing/legacy_joint_override.jsonl"
    )

    # --- SMS / OTP delivery ---
    # Firebase dispatches phone-auth SMS on the Android client; the backend only
    # verifies the resulting ID token. MSG91 remains the existing server seam.
    otp_provider: Literal["mock", "firebase", "msg91"] = Field(default="mock")
    msg91_auth_key: str = Field(default="")
    msg91_sender_id: str = Field(default="AGROAI")
    msg91_template_id: str = Field(default="")
    msg91_base_url: str = Field(default="https://control.msg91.com/api/v5")

    # --- Today's Farm Task advisory layer (2026-09) ---
    # Master switch for the whole daily-task feature (signal generation +
    # farmer-facing cards). Off by default until a pilot cohort is enabled,
    # matching the same "release decision is a config change" pattern as
    # `openai_vision_diagnosis_enabled` above.
    daily_tasks_enabled: bool = Field(default=False)
    # Sub-flag: the uneven-growth zonal tracking signal. Today's Farm Task
    # can launch with this off -- the other MVP task types are unaffected
    # (see app/modules/daily_task/zonal_analysis.py).
    uneven_growth_enabled: bool = Field(default=False)
    # Evidence Pack generation (the on-demand damage-evidence record). Can
    # launch independently of daily_tasks_enabled and independently of the
    # PDF export below (text/data-only pack).
    evidence_pack_enabled: bool = Field(default=False)
    # PDF export for an Evidence Pack. Off by default: no Tamil-capable font
    # is bundled yet, so the PDF is English-only (see evidence_pack.py) --
    # this flag lets that ship later without touching the pack itself.
    evidence_pack_pdf_enabled: bool = Field(default=False)
    # Present for forward compatibility with a future satellite-side "zonal
    # analysis" concept distinct from the daily-task zone tracker above.
    # Currently unused by any code path; kept so a later split does not need
    # a new flag name.
    zonal_analysis_enabled: bool = Field(default=False)
    # Gate on the drainage/waterlogging daily-task signal specifically. Must
    # stay off (or the underlying satellite waterlogging policy gate must
    # stay in place) until the caution-language review is signed off --
    # see app/modules/satellite/waterlogging.py and daily_task/signal_providers.py.
    cautious_waterlogging_tasks_enabled: bool = Field(default=False)

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

    @property
    def async_database_url(self) -> str:
        """Database URL adapted for SQLAlchemy's async engine."""
        return normalize_async_database_url(self.database_url)

    @property
    def migration_async_database_url(self) -> str:
        """Connection used for Alembic migrations only (needs DDL privileges).

        Falls back to the runtime DATABASE_URL if MIGRATION_DATABASE_URL is unset,
        so nothing breaks in environments that have not set it up.
        """
        if self.migration_database_url:
            return normalize_async_database_url(self.migration_database_url)
        return self.async_database_url

    @property
    def openai_vision_diagnosis_enabled(self) -> bool:
        return bool(self.openai_vision_diagnosis_api_key and self.openai_vision_diagnosis_model)

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
        if not self.admin_web_origins or any(
            not origin.startswith("https://") for origin in self.admin_web_origins
        ):
            problems.append("ADMIN_WEB_ORIGINS must contain explicit HTTPS origins.")
        elif any(origin not in self.cors_origins for origin in self.admin_web_origins):
            problems.append("Every ADMIN_WEB_ORIGINS entry must also be present in CORS_ORIGINS.")
        if not self.admin_session_cookie_name.startswith("__Host-"):
            problems.append("ADMIN_SESSION_COOKIE_NAME must use the __Host- prefix.")
        if not self.admin_require_mfa:
            problems.append("ADMIN_REQUIRE_MFA must be true in production.")
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
        if self.otp_provider == "msg91":
            problems.append(
                "OTP_PROVIDER=msg91 is not connected to the production auth flow; "
                "use Firebase Phone Auth."
            )
        if problems:
            raise ProductionConfigError("Refusing to boot production: " + " ".join(problems))


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()


