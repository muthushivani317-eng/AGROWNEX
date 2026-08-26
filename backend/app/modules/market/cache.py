"""Market cache layer (docs/API_CONTRACT.md → Market Prices cache 15 minutes).

Caches the normalized price query behind the shared cache seam
(``app.core.cache``): process-local in dev/tests, Redis-backed in production
(``CACHE_BACKEND=redis``) without touching the service.
"""
from __future__ import annotations

from typing import Any

from app.core.cache import Cache, build_cache
from app.modules.market.constants import MARKET_CACHE_TTL_SECONDS
from app.modules.market.provider import PriceQuery


class MarketCache:
    def __init__(
        self,
        ttl_seconds: int = MARKET_CACHE_TTL_SECONDS,
        *,
        backend: Cache | None = None,
    ) -> None:
        self.ttl = ttl_seconds
        self._backend = backend or build_cache(
            namespace="market", ttl_seconds=ttl_seconds
        )

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
        return self._backend.get(key)

    def set(self, key: str, value: Any) -> None:
        self._backend.set(key, value)

    def delete(self, key: str) -> None:
        self._backend.delete(key)

    def clear(self) -> None:
        self._backend.clear()


# Process-wide singleton so cached prices are shared across requests.
market_cache = MarketCache()
