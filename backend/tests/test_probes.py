"""Liveness/readiness probe tests (Phase 3)."""
from __future__ import annotations

from app.api.probes import build_readiness
from app.api.probes import router as probes_router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_healthz_liveness():
    app = FastAPI()
    app.include_router(probes_router)
    res = TestClient(app).get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_readiness_ready_when_all_ok():
    status_code, body = build_readiness(db_ok=True, redis_ok=True)
    assert status_code == 200
    assert body == {
        "status": "ready",
        "database": "ok",
        "redis": "ok",
        "disease_model": "ok",
    }


def test_readiness_503_when_db_down():
    status_code, body = build_readiness(db_ok=False, redis_ok=True)
    assert status_code == 503
    assert body["status"] == "not_ready"
    assert body["database"] == "unavailable"


def test_readiness_503_when_redis_down():
    status_code, body = build_readiness(db_ok=True, redis_ok=False)
    assert status_code == 503
    assert body["redis"] == "unavailable"


def test_readiness_503_when_required_disease_model_down():
    status_code, body = build_readiness(db_ok=True, redis_ok=True, model_ok=False)
    assert status_code == 503
    assert body["disease_model"] == "unavailable"
