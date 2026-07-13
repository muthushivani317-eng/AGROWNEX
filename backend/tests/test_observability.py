"""Observability tests (Phase 4): metrics endpoint, log scrubbing, Sentry no-op."""
from __future__ import annotations

from app.api.errors import register_exception_handlers
from app.api.probes import router as probes_router
from app.core.config import settings
from app.core.logging import _scrub, init_sentry
from app.core.metrics import Metrics, metrics
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(probes_router)
    return app


# --------------------------------------------------------------------------- #
# /metrics
# --------------------------------------------------------------------------- #
def test_metrics_forbidden_without_token(monkeypatch):
    monkeypatch.setattr(settings, "metrics_token", "secret-token")
    res = TestClient(_app()).get("/metrics")
    assert res.status_code == 403


def test_metrics_closed_when_no_token_configured(monkeypatch):
    monkeypatch.setattr(settings, "metrics_token", "")
    res = TestClient(_app()).get("/metrics", headers={"X-Metrics-Token": "anything"})
    assert res.status_code == 403


def test_metrics_exposed_with_valid_token(monkeypatch):
    monkeypatch.setattr(settings, "metrics_token", "secret-token")
    res = TestClient(_app()).get("/metrics", headers={"X-Metrics-Token": "secret-token"})
    assert res.status_code == 200
    assert "agrowai_requests_total" in res.text


def test_metrics_counts_ai_calls():
    m = Metrics()
    m.observe_ai_call("gemini-2.5-flash")
    m.observe_ai_call("gemini-2.5-flash")
    m.observe_ai_call("gemini-2.5-pro")
    out = m.render()
    assert 'agrowai_ai_calls_total{model="gemini-2.5-flash"} 2' in out
    assert 'agrowai_ai_calls_total{model="gemini-2.5-pro"} 1' in out


def test_request_metrics_recorded():
    metrics.reset()
    metrics.observe_request(status_code=200, latency_ms=12.0)
    metrics.observe_request(status_code=500, latency_ms=8.0)
    assert metrics.requests_total == 2
    assert metrics.errors_total == 1


# --------------------------------------------------------------------------- #
# Log scrubbing — never log OTPs, phone numbers, or auth tokens
# --------------------------------------------------------------------------- #
def test_scrub_redacts_otp():
    assert "123456" not in _scrub("otp=123456 sent")


def test_scrub_redacts_phone_middle_digits():
    scrubbed = _scrub("user +919876543210 called")
    assert "9876543" not in scrubbed


def test_scrub_redacts_authorization():
    # The credential must be gone; a "Bearer" label may remain.
    scrubbed = _scrub("authorization: Bearer abc.def.ghi")
    assert "abc.def.ghi" not in scrubbed


# --------------------------------------------------------------------------- #
# Sentry is a safe no-op when unconfigured
# --------------------------------------------------------------------------- #
def test_sentry_noop_without_dsn(monkeypatch):
    monkeypatch.setattr(settings, "sentry_dsn", "")
    assert init_sentry() is False
