"""Relay contract: fail-closed auth, host allow-list, pass-through, error mapping."""
from __future__ import annotations

import base64
import importlib
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def relay(monkeypatch):
    monkeypatch.setenv("RELAY_TOKEN", "secret-token")
    import main

    module = importlib.reload(main)
    return module


def _mock_upstream(module, handler):
    module._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


AUTH = {"Authorization": "Bearer secret-token"}


def test_rejects_missing_or_wrong_token(relay):
    client = TestClient(relay.app)
    body = {"method": "GET", "url": "https://api.data.gov.in/resource/x"}
    assert client.post("/fetch", json=body).status_code == 401
    wrong = client.post("/fetch", json=body, headers={"Authorization": "Bearer nope"})
    assert wrong.status_code == 401
    assert wrong.headers["x-relay-error"] == "unauthorized"


def test_fails_closed_without_configured_token(monkeypatch):
    monkeypatch.setenv("RELAY_TOKEN", "")
    import main

    module = importlib.reload(main)
    client = TestClient(module.app)
    res = client.post(
        "/fetch",
        json={"method": "GET", "url": "https://api.data.gov.in/x"},
        headers={"Authorization": "Bearer "},
    )
    assert res.status_code == 401


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example.com/x",
        "http://api.data.gov.in/resource/x",  # plain http
        "https://api.data.gov.in:8443/x",  # odd port
        "https://user:pw@api.data.gov.in/x",
        "https://api.data.gov.in.evil.com/x",
    ],
)
def test_blocks_hosts_outside_allow_list(relay, url):
    res = TestClient(relay.app).post("/fetch", json={"method": "GET", "url": url}, headers=AUTH)
    assert res.status_code == 403
    assert res.headers["x-relay-error"] == "host_not_allowed"


def test_passes_through_status_body_and_forwards_only_safe_headers(relay):
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = request.content
        return httpx.Response(200, json={"data": [1]}, headers={"content-type": "application/json"})

    _mock_upstream(relay, handler)
    res = TestClient(relay.app).post(
        "/fetch",
        json={
            "method": "POST",
            "url": "https://api.agmarknet.gov.in/v1/prices-and-arrivals/x",
            "headers": {"Referer": "https://agmarknet.gov.in/", "Cookie": "leak", "Authorization": "x"},
            "body_b64": base64.b64encode(b"a=1&b=2").decode(),
        },
        headers=AUTH,
    )
    assert res.status_code == 200
    assert res.json() == {"data": [1]}
    assert res.headers["x-relay-upstream"] == "1"
    assert seen["body"] == b"a=1&b=2"
    assert seen["headers"]["referer"] == "https://agmarknet.gov.in/"
    assert "cookie" not in seen["headers"]
    assert "authorization" not in seen["headers"]


def test_upstream_error_status_is_passed_through(relay):
    _mock_upstream(relay, lambda r: httpx.Response(503, text="down"))
    res = TestClient(relay.app).post(
        "/fetch", json={"method": "GET", "url": "https://api.data.gov.in/x"}, headers=AUTH
    )
    assert res.status_code == 503
    assert res.headers["x-relay-upstream"] == "1"


def test_transport_failure_maps_to_502_relay_error(relay):
    def handler(request):
        raise httpx.ConnectError("reset", request=request)

    _mock_upstream(relay, handler)
    res = TestClient(relay.app).post(
        "/fetch", json={"method": "GET", "url": "https://api.data.gov.in/x"}, headers=AUTH
    )
    assert res.status_code == 502
    assert res.headers["x-relay-error"] == "upstream_unreachable"


def test_rejects_other_methods(relay):
    res = TestClient(relay.app).post(
        "/fetch", json={"method": "DELETE", "url": "https://api.data.gov.in/x"}, headers=AUTH
    )
    assert res.status_code == 422


def test_healthz(relay):
    assert TestClient(relay.app).get("/healthz").json() == {"status": "ok"}
