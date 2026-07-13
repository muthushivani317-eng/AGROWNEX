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


def test_rejects_debug_in_production():
    with pytest.raises(ProductionConfigError):
        _prod(debug=True).validate_production()
