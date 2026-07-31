"""Railway-compatible dependency-free liveness route tests."""
from __future__ import annotations

import app.api.probes as probes
from app.core import security
from app.modules.ai import constants as ai_constants
from app.modules.disease import ml_runtime
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(probes.router)
    return TestClient(app)


def test_health_is_public_dependency_free_liveness(monkeypatch):
    async def unexpected_dependency_call():
        raise AssertionError("liveness must not call readiness dependencies")

    def unexpected_model_load():
        raise AssertionError("liveness must not load a model runtime")

    class UnexpectedGeminiUse:
        def __bool__(self):
            raise AssertionError("liveness must not inspect Gemini configuration")

    monkeypatch.setattr(probes, "_check_db", unexpected_dependency_call)
    monkeypatch.setattr(probes, "_check_redis", unexpected_dependency_call)
    monkeypatch.setattr(security, "ensure_firebase_app", unexpected_model_load)
    monkeypatch.setattr(ai_constants, "GEMINI_API_KEY", UnexpectedGeminiUse())
    monkeypatch.setattr(ai_constants, "GEMINI_VISION_MODEL", UnexpectedGeminiUse())
    monkeypatch.setattr(ml_runtime, "get_model_runtime", unexpected_model_load)

    response = _client().get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok"}


def test_existing_healthz_alias_is_preserved():
    response = _client().get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_main_application_registers_railway_health_route():
    from app.main import create_app

    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_remains_not_found():
    assert _client().get("/not-a-probe").status_code == 404


def test_readyz_behaviour_is_unchanged(monkeypatch):
    async def database_ready():
        return True

    async def redis_ready():
        return True

    class ReadyRuntime:
        ready = True

    monkeypatch.setattr(probes, "_check_db", database_ready)
    monkeypatch.setattr(probes, "_check_redis", redis_ready)
    monkeypatch.setattr(ml_runtime, "get_model_runtime", lambda: ReadyRuntime())

    response = _client().get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "redis": "ok",
        "disease_model": "ok",
    }
