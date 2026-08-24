"""ARQ background worker (Phase 3 — scalability).

Run with: ``arq app.worker.WorkerSettings`` (see docker-compose ``worker`` service).
Uses the same Redis as the app. Each job opens its own DB session, commits on
success, and rolls back on error — the job *logic* lives in the modules
(`market.jobs`, `notifications.jobs`) and is unit-tested there without a worker.

Schedules:
* market price refresh — every 2 hours
* weather alert evaluation — every 30 minutes
* failed-notification retry — every 5 minutes
* produce offer expiry — once daily
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.metrics import metrics  # noqa: F401  (import warms the registry)
from app.modules.market.jobs import refresh_market_prices as _refresh_market_prices
from app.modules.notifications.jobs import (
    evaluate_weather_alerts as _evaluate_weather_alerts,
)
from app.modules.notifications.jobs import (
    retry_failed_notifications as _retry_failed_notifications,
)
from app.modules.produce.jobs import expire_stale_offers as _expire_stale_offers
from app.modules.satellite.jobs import render_satellite_images as _render_satellite_images

logger = get_logger("worker")


async def _run(job: Callable[[AsyncSession], Awaitable[dict]]) -> dict:
    async with SessionLocal() as session:
        try:
            result = await job(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            logger.exception("worker job %s failed", getattr(job, "__name__", job))
            raise


async def refresh_market_prices(ctx: dict[str, Any]) -> dict:
    return await _run(_refresh_market_prices)


async def evaluate_weather_alerts(ctx: dict[str, Any]) -> dict:
    return await _run(_evaluate_weather_alerts)


async def retry_failed_notifications(ctx: dict[str, Any]) -> dict:
    return await _run(_retry_failed_notifications)


async def expire_stale_offers(ctx: dict[str, Any]) -> dict:
    return await _run(_expire_stale_offers)


async def render_satellite_images_job(
    ctx: dict[str, Any], session_id: str, user_id: str
) -> dict[str, Any]:
    """Render and publish satellite layers outside the API process."""
    import uuid

    await _render_satellite_images(
        uuid.UUID(session_id), uuid.UUID(user_id), raise_on_error=True
    )
    return {"session_id": session_id, "rendered": True}


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [
        refresh_market_prices,
        evaluate_weather_alerts,
        retry_failed_notifications,
        expire_stale_offers,
        render_satellite_images_job,
    ]
    cron_jobs = [
        cron(refresh_market_prices, hour=set(range(0, 24, 2)), minute=0),
        cron(evaluate_weather_alerts, minute={0, 30}),
        cron(retry_failed_notifications, minute=set(range(0, 60, 5))),
        cron(expire_stale_offers, hour={3}, minute=0),
    ]
