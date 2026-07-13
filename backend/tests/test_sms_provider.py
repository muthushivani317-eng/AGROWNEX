"""MSG91 OTP provider selection + send (Phase 2 — HTTP mocked, no network)."""
from __future__ import annotations

import httpx
from app.core.config import settings
from app.modules.auth.sms import (
    MockSMSProvider,
    MSG91Provider,
    get_default_sms_provider,
    render_otp_message,
)


def test_default_provider_is_mock(monkeypatch):
    monkeypatch.setattr(settings, "otp_provider", "mock")
    assert isinstance(get_default_sms_provider(), MockSMSProvider)


def test_msg91_selected_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "otp_provider", "msg91")
    monkeypatch.setattr(settings, "msg91_auth_key", "key-123")
    assert isinstance(get_default_sms_provider(), MSG91Provider)


def test_msg91_without_key_falls_back_to_mock(monkeypatch):
    # A missing credential must never silently look like a real send.
    monkeypatch.setattr(settings, "otp_provider", "msg91")
    monkeypatch.setattr(settings, "msg91_auth_key", "")
    assert isinstance(get_default_sms_provider(), MockSMSProvider)


def test_otp_message_is_tamil_first():
    msg = render_otp_message("123456", ttl_minutes=5)
    assert "123456" in msg
    assert "நிமிட" in msg  # "minutes" in Tamil — message is Tamil-first


def _mock_httpx(monkeypatch, handler) -> None:
    real = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real(transport=transport, timeout=kw.get("timeout")),
    )


async def test_msg91_send_success(monkeypatch):
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authkey"] = request.headers.get("authkey")
        return httpx.Response(200, json={"type": "success"})

    _mock_httpx(monkeypatch, handler)
    provider = MSG91Provider(auth_key="key-123", template_id="tmpl-1")
    ok = await provider.send_otp("+919876500000", "123456", ttl_minutes=5)
    assert ok is True
    assert seen["authkey"] == "key-123"


async def test_msg91_send_failure_returns_false(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"type": "error"})

    _mock_httpx(monkeypatch, handler)
    provider = MSG91Provider(auth_key="key-123", template_id="tmpl-1")
    ok = await provider.send_otp("+919876500000", "123456", ttl_minutes=5)
    assert ok is False
