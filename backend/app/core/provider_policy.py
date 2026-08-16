"""Shared guard for deterministic feature mocks.

Mocks are injectable test fixtures. They may be selected from environment only in
explicit local development/test processes, never in pilot, field-test, or production.
"""
from __future__ import annotations

import os


def test_mocks_enabled() -> bool:
    environment = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    requested = os.getenv("AGROWAI_ENABLE_TEST_MOCKS", "").lower() in {"1", "true", "yes"}
    return requested and environment in {"development", "dev", "test", "testing"}
