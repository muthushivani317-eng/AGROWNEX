"""Kubernetes-style liveness/readiness probes (Phase 3 — reliability).

``/healthz`` is a dependency-free liveness check (is the process up?).
``/readyz`` verifies the app can actually serve traffic: the database responds
and, when Redis is the configured cache/rate-limit backend, Redis responds too.
Returns 503 when not ready so orchestrators stop routing to a broken pod.

The existing ``/api/v1/health`` endpoints are kept as backward-compatible aliases.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger

logger = get_logger("probes")
router = APIRouter(tags=["probes"])


def build_readiness(*, db_ok: bool, redis_ok: bool) -> tuple[int, dict]:
    """Pure readiness verdict from component checks (unit-tested without infra)."""
    ready = db_ok and redis_ok
    body = {
        "status": "ready" if ready else "not_ready",
        "database": "ok" if db_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
    }
    return (200 if ready else 503), body


async def _check_db() -> bool:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - readiness must never raise
        logger.warning("readiness: database check failed")
        return False


async def _check_redis() -> bool:
    # Redis is only *required* when it backs the cache/rate limiter.
    if settings.cache_backend.lower() != "redis":
        return True
    try:
        import redis.asyncio as redis_asyncio

        client = redis_asyncio.from_url(settings.redis_url)
        try:
            await client.ping()
        finally:
            await client.aclose()
        return True
    except Exception:  # noqa: BLE001
        logger.warning("readiness: redis check failed")
        return False


@router.get("/healthz")
async def healthz():
    """Liveness — always fast, no dependencies."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz():
    """Readiness — DB (+ Redis when configured) must be reachable."""
    status_code, body = build_readiness(
        db_ok=await _check_db(), redis_ok=await _check_redis()
    )
    return JSONResponse(status_code=status_code, content=body)
