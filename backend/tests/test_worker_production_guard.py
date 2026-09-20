"""The worker must refuse to boot on an unsafe production config, exactly
like the API process does (app/main.py's create_app()). Both processes share
the same `settings` object; before this guard, only the API side called
`settings.validate_production()`, so a bad production config would crash the
API on startup but leave the worker running background jobs against
production data undetected.
"""
from __future__ import annotations

import pytest

from app.core.config import ProductionConfigError, settings
from app.worker import WorkerSettings, on_startup


def test_worker_settings_declares_on_startup_hook():
    assert WorkerSettings.on_startup is on_startup


async def test_worker_on_startup_calls_validate_production(monkeypatch):
    calls: list[bool] = []
    monkeypatch.setattr(
        type(settings), "validate_production", lambda self: calls.append(True)
    )
    await on_startup({})
    assert calls == [True]


async def test_worker_on_startup_propagates_unsafe_production_config(monkeypatch):
    def _raise(self):
        raise ProductionConfigError("Refusing to boot production: DEBUG must be false.")

    monkeypatch.setattr(type(settings), "validate_production", _raise)
    with pytest.raises(ProductionConfigError):
        await on_startup({})
