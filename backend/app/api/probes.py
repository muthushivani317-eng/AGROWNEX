"""Kubernetes-style liveness/readiness probes (Phase 3 — reliability).

``/healthz`` is a dependency-free liveness check (is the process up?).
``/readyz`` verifies the app can actually serve traffic: the database responds
and, when Redis is the configured cache/rate-limit backend, Redis responds too.
Returns 503 when not ready so orchestrators stop routing to a broken pod.

The existing ``/api/v1/health`` endpoints are kept as backward-compatible aliases.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import ForbiddenError
from app.core.logging import get_logger
from app.core.metrics import metrics

logger = get_logger("probes")
router = APIRouter(tags=["probes"])


def build_readiness(*, db_ok: bool, redis_ok: bool, model_ok: bool = True) -> tuple[int, dict]:
    """Pure readiness verdict from component checks (unit-tested without infra)."""
    ready = db_ok and redis_ok and model_ok
    body = {
        "status": "ready" if ready else "not_ready",
        "database": "ok" if db_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
        "disease_model": "ok" if model_ok else "unavailable",
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
    from app.modules.disease.ml_runtime import get_model_runtime

    status_code, body = build_readiness(
        db_ok=await _check_db(),
        redis_ok=await _check_redis(),
        model_ok=(not settings.disease_model_required or get_model_runtime().ready),
    )
    return JSONResponse(status_code=status_code, content=body)


@router.get("/ready")
async def controlled_pilot_readiness():
    """Fail-closed readiness for the controlled six-crop KVK pilot.

    The response exposes component categories only—never credentials, artifact
    paths, hashes, provider hostnames, or model configuration values.
    """
    from app.core.security import ensure_firebase_app
    from app.crop_runtime.readiness import ReadinessResolver
    from app.crop_runtime.registry import load_registry
    from app.modules.ai.constants import GEMINI_API_KEY, GEMINI_VISION_MODEL

    crops = ("banana", "paddy", "cotton", "groundnut", "redgram", "chilli")
    registry = load_registry()
    resolver = ReadinessResolver(registry, Path(__file__).resolve().parents[2])
    runtime_status = {}
    for crop_id in crops:
        try:
            runtime_status[crop_id] = resolver.resolve(crop_id).runtime_loadable
        except Exception:  # noqa: BLE001 - readiness must fail closed
            runtime_status[crop_id] = False
    components = {
        "database": await _check_db(),
        "redis": await _check_redis(),
        "firebase": ensure_firebase_app() is not None,
        "gemini_configured": bool(GEMINI_API_KEY and GEMINI_VISION_MODEL),
        "six_runtimes": runtime_status,
        "recommendation_pipeline_blocked": True,
    }
    ready = (
        components["database"]
        and components["redis"]
        and components["firebase"]
        and components["gemini_configured"]
        and all(runtime_status.values())
        and components["recommendation_pipeline_blocked"]
    )
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", **components},
    )


@router.get("/metrics")
async def prometheus_metrics(x_metrics_token: str | None = Header(default=None)):
    """Prometheus metrics, guarded by an internal token (403 unless it matches)."""
    if not settings.metrics_token or x_metrics_token != settings.metrics_token:
        raise ForbiddenError("Metrics access denied.")
    return PlainTextResponse(metrics.render())
