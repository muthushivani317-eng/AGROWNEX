"""Tests for the shared cache seam (Phase 1 — Redis caching for idempotent reads)."""
from __future__ import annotations

from app.core.cache import InMemoryTTLCache, RedisTTLCache


# --------------------------------------------------------------------------- #
# In-memory backend
# --------------------------------------------------------------------------- #
def test_in_memory_set_get_and_miss():
    cache = InMemoryTTLCache(namespace="t", ttl_seconds=60)
    assert cache.get("k") is None
    cache.set("k", {"v": 1})
    assert cache.get("k") == {"v": 1}


def test_in_memory_expiry_and_clear():
    expired = InMemoryTTLCache(namespace="t", ttl_seconds=-1)
    expired.set("k", "v")
    assert expired.get("k") is None  # already expired

    cache = InMemoryTTLCache(namespace="t", ttl_seconds=60)
    cache.set("k", "v")
    cache.clear()
    assert cache.get("k") is None


# --------------------------------------------------------------------------- #
# Redis backend (fake client — no network)
# --------------------------------------------------------------------------- #
class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str):
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value

    def scan_iter(self, pattern: str):
        return list(self.store.keys())

    def delete(self, key: str):
        self.store.pop(key, None)


class _BrokenRedis:
    def get(self, key: str):
        raise ConnectionError("redis down")

    def setex(self, key: str, ttl: int, value: str):
        raise ConnectionError("redis down")

    def scan_iter(self, pattern: str):
        raise ConnectionError("redis down")

    def delete(self, key: str):
        raise ConnectionError("redis down")


def test_redis_json_round_trip_and_namespacing():
    fake = _FakeRedis()
    cache = RedisTTLCache(
        namespace="weather", ttl_seconds=60, redis_url="", client=fake
    )
    cache.set("12.9:80.1", {"temp": 30})
    assert cache.get("12.9:80.1") == {"temp": 30}
    assert "weather:12.9:80.1" in fake.store  # namespaced key


def test_redis_degrades_gracefully_to_memory_when_down():
    cache = RedisTTLCache(
        namespace="market", ttl_seconds=60, redis_url="", client=_BrokenRedis()
    )
    # A read while Redis is down must not raise, and the local fallback still works.
    assert cache.get("paddy") is None
    cache.set("paddy", True)
    assert cache.get("paddy") is True
