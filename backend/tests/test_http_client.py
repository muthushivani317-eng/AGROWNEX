"""Shared HTTP client tests (Phase 3 — connection reuse)."""
from __future__ import annotations

from app.core.http import close_http_client, get_http_client


async def test_client_is_reused_across_calls():
    c1 = get_http_client()
    c2 = get_http_client()
    assert c1 is c2  # one pooled client, not a new one per call
    await close_http_client()


async def test_client_recreated_after_close():
    c1 = get_http_client()
    await close_http_client()
    c2 = get_http_client()
    assert c1 is not c2
    await close_http_client()
