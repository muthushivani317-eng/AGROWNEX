"""Kubernetes-style liveness/readiness probes (Phase 3 — reliability).

``/health`` and ``/healthz`` are dependency-free liveness checks (is the process up?).
``/readyz`` verifies the app can actually serve traffic: the database responds
and, when Redis is the configured cache/rate-limit backend, Redis responds too.
Returns 503 when not ready so orchestrators stop routing to a broken pod.

The existing ``/api/v1/health`` endpoints are kept as backward-compatible aliases.
"""

from __future__ import annotations

import asyncio
import hmac
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
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


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


async def _check_disease_models() -> bool:
    """Verify the controlled crop inventory used by production inference.

    The legacy single-model runtime is no longer the production disease path.
    Readiness must follow the safety-gated six-crop inventory instead.
    """
    if not settings.disease_model_required:
        return True
    try:
        from app.crop_runtime.inventory import get_model_inventory, inventory_ready

        inventory = await asyncio.to_thread(get_model_inventory)
        return inventory_ready(inventory)
    except Exception:  # noqa: BLE001 - readiness must never raise
        logger.warning("readiness: controlled disease inventory check failed")
        return False


@router.get("/health")
@router.get("/healthz")
async def healthz():
    """Liveness — always fast, no dependencies."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz():
    """Readiness — DB (+ Redis when configured) must be reachable."""
    status_code, body = build_readiness(
        db_ok=await _check_db(),
        redis_ok=await _check_redis(),
        model_ok=await _check_disease_models(),
    )
    return JSONResponse(status_code=status_code, content=body)


@router.get("/ready")
async def controlled_pilot_readiness():
    """Fail-closed readiness for the controlled six-crop KVK pilot.

    The response exposes component categories only—never credentials, artifact
    paths, hashes, provider hostnames, or model configuration values.
    """
    from app.core.security import ensure_firebase_app
    from app.crop_runtime.inventory import get_model_inventory, inventory_ready
    from app.modules.ai.constants import GEMINI_API_KEY, GEMINI_VISION_MODEL

    inventory = await asyncio.to_thread(get_model_inventory)
    runtime_status = inventory.disease_runtimes
    runtime_diagnostics = {
        crop_id: reason
        for crop_id, reason in inventory.runtime_diagnostics.items()
        if crop_id in {"redgram", "chilli"} and reason != "ready"
    }
    for crop_id, reason in runtime_diagnostics.items():
        logger.warning(
            "controlled pilot runtime readiness failed",
            extra={"crop_id": crop_id, "category": reason},
        )
    components = {
        "database": await _check_db(),
        "redis": await _check_redis(),
        "firebase": ensure_firebase_app() is not None,
        # Informational only: local controlled inference does not require Gemini.
        "gemini_configured": bool(GEMINI_API_KEY and GEMINI_VISION_MODEL),
        "six_runtimes": runtime_status,
        "runtime_diagnostics": runtime_diagnostics,
        "inference_dependencies": inventory.dependencies,
        "crop_identity_runtime": inventory.crop_identity_ready,
        "crop_identity_safety_gate": inventory.safety_gate_ready,
        "recommendation_pipeline_blocked": True,
    }
    ready = (
        components["database"]
        and components["redis"]
        and components["firebase"]
        and inventory_ready(inventory)
        and components["recommendation_pipeline_blocked"]
    )
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", **components},
    )


@router.get("/metrics")
async def prometheus_metrics(x_metrics_token: str | None = Header(default=None)):
    """Prometheus metrics, guarded by an internal token (403 unless it matches)."""
    if not settings.metrics_token or not x_metrics_token or not hmac.compare_digest(
        x_metrics_token.encode(), settings.metrics_token.encode()
    ):
        raise ForbiddenError("Metrics access denied.")
    return PlainTextResponse(metrics.render())
