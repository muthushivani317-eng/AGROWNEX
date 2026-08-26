"""Production boot-guard tests (Phase 2 — fail fast on unsafe config)."""
from __future__ import annotations

import pytest
from app.core.config import DEV_SESSION_SECRET, ProductionConfigError, Settings


def _prod(**overrides) -> Settings:
    base = dict(
        environment="production",
        debug=False,
        session_secret="a-real-production-secret",
        cors_origins=["https://app.agrowai.in"],
        admin_web_origins=["https://admin.agrowai.in"],
        admin_session_cookie_name="__Host-agrowai_admin",
        admin_require_mfa=True,
        public_api_url="https://api.agrowai.in",
        trusted_hosts=["api.agrowai.in"],
        database_url="postgresql+asyncpg://app:secret@db.internal:5432/agrowai",
        redis_url="redis://redis.internal:6379/0",
        firebase_project_id="agrowai-production",
        firebase_credentials_json='{"type":"service_account"}',
        otp_provider="firebase",
    )
    base.update(overrides)
    return Settings(**base)


def test_valid_production_config_boots():
    _prod().validate_production()  # must not raise


def test_development_is_never_blocked():
    Settings(environment="development").validate_production()  # no raise


def test_rejects_dev_secret_in_production():
    with pytest.raises(ProductionConfigError):
        _prod(session_secret=DEV_SESSION_SECRET).validate_production()


def test_rejects_wildcard_cors_in_production():
    with pytest.raises(ProductionConfigError):
        _prod(cors_origins=["*"]).validate_production()


def test_rejects_empty_cors_in_production():
    with pytest.raises(ProductionConfigError):
        _prod(cors_origins=[]).validate_production()


@pytest.mark.parametrize("origins", [[], ["http://admin.agrowai.in"]])
def test_rejects_missing_or_insecure_admin_origin(origins):
    with pytest.raises(ProductionConfigError):
        _prod(admin_web_origins=origins).validate_production()


def test_rejects_debug_in_production():
    with pytest.raises(ProductionConfigError):
        _prod(debug=True).validate_production()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("public_api_url", "http://api.agrowai.in"),
        ("public_api_url", "https://localhost:8000"),
        ("trusted_hosts", ["*"]),
        ("database_url", "postgresql+asyncpg://app:secret@localhost/agrowai"),
        ("redis_url", "redis://localhost:6379/0"),
        ("firebase_project_id", ""),
        ("firebase_credentials_json", ""),
        ("firebase_auth_emulator_host", "127.0.0.1:9099"),
        ("otp_provider", "mock"),
    ],
)
def test_rejects_unsafe_production_dependencies(field, value):
    with pytest.raises(ProductionConfigError):
        _prod(**{field: value}).validate_production()


def test_nonproduction_firebase_emulator_is_allowed():
    Settings(
        environment="test",
        firebase_project_id="demo-agrowai-crop-id-test",
        firebase_auth_emulator_host="127.0.0.1:9099",
    ).validate_production()
