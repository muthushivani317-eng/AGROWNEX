"""Gemini client resilience: a malformed (non-JSON) response body must not
crash the request with an unhandled exception (2026-08 pre-release audit).

Previously `response.json()` was called unguarded inside the retry loop, so a
2xx response with a truncated or non-JSON body (e.g. a proxy timeout page)
propagated as a raw, unhandled `json.JSONDecodeError` instead of the
`AIUnavailableError` every other Gemini failure mode produces — meaning a
farmer would see a generic server error instead of the app's normal
"AI is unavailable" fallback UI.
"""
from __future__ import annotations

import json

import httpx
import pytest
from app.modules.ai.constants import GEMINI_SAFETY_SETTINGS
from app.modules.ai.exceptions import AIUnavailableError
from app.modules.ai.provider import GeminiClient


async def _no_sleep(_delay: float) -> None:
    return None


async def test_non_json_response_is_retried_then_fails_closed(monkeypatch):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        # A 200 with a body that isn't valid JSON (e.g. an upstream/proxy
        # error page returned with the wrong status).
        return httpx.Response(200, content=b"<html>bad gateway</html>", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr("app.modules.ai.provider.get_http_client", lambda: client)
    monkeypatch.setattr("app.modules.ai.provider.asyncio.sleep", _no_sleep)

    with pytest.raises(AIUnavailableError):
        await GeminiClient(api_key="k", max_retries=3).generate(
            system="", history=[], message="hi"
        )

    await client.aclose()
    assert calls == 3  # bounded retries, not an unhandled crash


async def test_non_json_response_recovers_on_a_later_retry(monkeypatch):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, content=b"not json", request=request)
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "hello"}]}}],
                "usageMetadata": {},
            },
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr("app.modules.ai.provider.get_http_client", lambda: client)
    monkeypatch.setattr("app.modules.ai.provider.asyncio.sleep", _no_sleep)

    result = await GeminiClient(api_key="k", max_retries=3).generate(
        system="", history=[], message="hi"
    )

    await client.aclose()
    assert result.text == "hello"
    assert calls == 2


async def test_every_request_sends_explicit_safety_settings(monkeypatch):
    """2026-08 pre-release audit: previously safetySettings was never sent,
    so every chat silently relied on Gemini's undocumented default
    thresholds instead of an explicit, reviewable configuration."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
                "usageMetadata": {},
            },
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr("app.modules.ai.provider.get_http_client", lambda: client)

    await GeminiClient(api_key="k").generate(system="s", history=[], message="hi")
    await client.aclose()

    assert captured["json"]["safetySettings"] == GEMINI_SAFETY_SETTINGS
    categories = {entry["category"] for entry in captured["json"]["safetySettings"]}
    assert categories == {
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
    }
