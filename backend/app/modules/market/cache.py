"""Market cache layer (docs/API_CONTRACT.md → Market Prices cache 15 minutes).

An in-process TTL cache keyed by the normalized price query. The interface is
deliberately tiny so a Redis-backed implementation can replace it in production
without touching the service (docs/BACKEND_ARCHITECTURE.md → Redis cache).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.modules.market.constants import MARKET_CACHE_TTL_SECONDS
from app.modules.market.provider import PriceQuery


@dataclass
class _Entry:
    value: Any
    expires_at: float


class MarketCache:
    def __init__(self, ttl_seconds: int = MARKET_CACHE_TTL_SECONDS) -> None:
        self.ttl = ttl_seconds
        self._store: dict[str, _Entry] = {}

    @staticmethod
    def key(query: PriceQuery) -> str:
        parts = [
            (query.commodity or "").strip().lower(),
            (query.market or "").strip().lower(),
            (query.district or "").strip().lower(),
            (query.state or "").strip().lower(),
        ]
        return "|".join(parts)

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = _Entry(value=value, expires_at=time.monotonic() + self.ttl)

    def clear(self) -> None:
        self._store.clear()


# Process-wide singleton so cached prices are shared across requests.
market_cache = MarketCache()
