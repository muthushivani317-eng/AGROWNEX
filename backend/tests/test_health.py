"""Smoke tests for the app skeleton — no database required."""
from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_liveness_returns_ok_envelope() -> None:
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    # Standard envelope fields (docs/API_CONTRACT.md).
    assert "timestamp" in body
    assert "request_id" in body


def test_unknown_route_returns_error_envelope() -> None:
    res = client.get("/api/v1/does-not-exist")
    assert res.status_code == 404


def test_openapi_schema_available() -> None:
    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert res.json()["info"]["title"] == "AgrowAI API"
