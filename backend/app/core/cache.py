"""Shared response cache seam (Phase 1 — Redis caching for idempotent reads).

Only *idempotent, non-personalized* reads are cached here — weather bundles and
market prices — with short TTLs (docs/API_CONTRACT.md → CACHING). Disease
diagnoses and personalized chat are **never** cached: a farmer's crop decision
must reflect the photo in front of them, not a stale answer.

Two interchangeable backends implement the same tiny sync contract so a module's
cache can be swapped from in-process to Redis without touching its service:

* ``InMemoryTTLCache`` — process-local TTL dict (default; used in dev/tests).
* ``RedisTTLCache``    — Redis-backed, JSON-serialized, shared across workers.

The Redis backend **degrades gracefully**: if Redis is unreachable it falls back
to a local TTL cache for that operation and logs, so a Redis blip never takes
down weather or market for a farmer.
"""
from __future__ import annotations

import json
import time
from typing import Any, Protocol

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("core.cache")


class Cache(Protocol):
    """The minimal cache contract the module caches depend on."""

    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...


class InMemoryTTLCache:
    """A process-local TTL cache keyed by namespace:key."""

    def __init__(self, *, namespace: str, ttl_seconds: int) -> None:
        self.namespace = namespace
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at <= time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.monotonic() + self.ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


class RedisTTLCache:
    """Redis-backed cache with JSON values and graceful degradation to memory."""

    def __init__(
        self,
        *,
        namespace: str,
        ttl_seconds: int,
        redis_url: str,
        client: Any | None = None,
    ) -> None:
        self.namespace = namespace
        self.ttl = ttl_seconds
        self._fallback = InMemoryTTLCache(namespace=namespace, ttl_seconds=ttl_seconds)
        if client is not None:
            self._client = client
        else:  # pragma: no cover - trivial construction path
            import redis  # local import: only needed when Redis is the backend

            self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def _k(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    def get(self, key: str) -> Any | None:
        try:
            raw = self._client.get(self._k(key))
        except Exception as exc:  # noqa: BLE001 - never fail a read on cache trouble
            logger.warning("redis cache get failed (%s); using local fallback", exc)
            return self._fallback.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    def set(self, key: str, value: Any) -> None:
        try:
            self._client.setex(self._k(key), self.ttl, json.dumps(value))
        except Exception as exc:  # noqa: BLE001 - caching is best-effort
            logger.warning("redis cache set failed (%s); using local fallback", exc)
            self._fallback.set(key, value)

    def delete(self, key: str) -> None:
        try:
            self._client.delete(self._k(key))
        except Exception as exc:  # noqa: BLE001 - caching is best-effort
            logger.warning("redis cache delete failed (%s)", exc)
        self._fallback.delete(key)

    def clear(self) -> None:
        try:
            for k in self._client.scan_iter(f"{self.namespace}:*"):
                self._client.delete(k)
        except Exception as exc:  # noqa: BLE001
            logger.warning("redis cache clear failed (%s)", exc)
        self._fallback.clear()


def build_cache(*, namespace: str, ttl_seconds: int) -> Cache:
    """Return the configured cache backend for a module.

    ``CACHE_BACKEND=redis`` selects the shared Redis cache in production; any other
    value (default ``memory``) uses the process-local TTL cache so dev and tests
    need no Redis.
    """
    if settings.cache_backend.lower() == "redis":
        logger.info("cache backend: redis (namespace=%s ttl=%ss)", namespace, ttl_seconds)
        return RedisTTLCache(
            namespace=namespace, ttl_seconds=ttl_seconds, redis_url=settings.redis_url
        )
    return InMemoryTTLCache(namespace=namespace, ttl_seconds=ttl_seconds)
