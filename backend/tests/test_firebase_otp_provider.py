"""Production guards for Firebase client-dispatched phone authentication."""

from __future__ import annotations

import pytest
from app.core.config import DEV_SESSION_SECRET, ProductionConfigError, Settings
from app.modules.auth.sms import get_default_sms_provider
from pydantic import ValidationError


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "production",
        "debug": False,
        "public_api_url": "https://api.example.invalid",
        "trusted_hosts": ["api.example.invalid"],
        "database_url": "postgresql+asyncpg://user:pass@db.internal/agrowai",
        "redis_url": "redis://redis.internal:6379/0",
        "session_secret": "production-test-secret-at-least-32-characters",
        "cors_origins": ["https://app.example.invalid"],
        "firebase_project_id": "test-project",
        "firebase_credentials_json": '{"type":"service_account"}',
        "otp_provider": "firebase",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_firebase_provider_is_valid_with_admin_configuration() -> None:
    production_settings().validate_production()


@pytest.mark.parametrize("missing", ["firebase_project_id", "firebase_credentials_json"])
def test_firebase_provider_requires_admin_configuration(missing: str) -> None:
    settings = production_settings(**{missing: ""})
    with pytest.raises(ProductionConfigError, match="Firebase Admin credentials"):
        settings.validate_production()


def test_mock_provider_remains_forbidden_in_production() -> None:
    settings = production_settings(otp_provider="mock")
    with pytest.raises(ProductionConfigError, match="OTP_PROVIDER=mock"):
        settings.validate_production()


def test_msg91_configuration_behavior_is_unchanged() -> None:
    production_settings(otp_provider="msg91").validate_production()


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        production_settings(otp_provider="disabled")


def test_firebase_sms_cannot_be_dispatched_by_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.auth.sms.settings.otp_provider", "firebase")
    with pytest.raises(RuntimeError, match="CLIENT_DISPATCHED"):
        get_default_sms_provider()


def test_production_fixture_does_not_use_dev_secret() -> None:
    assert production_settings().session_secret != DEV_SESSION_SECRET
