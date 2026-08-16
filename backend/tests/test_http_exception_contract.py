from __future__ import annotations

from app.api.errors import register_exception_handlers
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def _client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/typed")
    async def typed():
        raise HTTPException(
            503,
            detail={"code": "MODEL_INTEGRITY_FAILURE", "message": "Model unavailable."},
            headers={"Retry-After": "30"},
        )

    return TestClient(app)


def test_http_exception_uses_standard_error_envelope() -> None:
    response = _client().get("/typed", headers={"X-Request-ID": "request-123"})

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "30"
    assert response.json() == {
        "success": False,
        "message": "Model unavailable.",
        "error_code": "MODEL_INTEGRITY_FAILURE",
        "errors": [],
        "timestamp": response.json()["timestamp"],
        "request_id": "request-123",
    }
