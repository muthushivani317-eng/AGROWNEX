"""Best-effort satellite enrichment jobs.

Numeric indices are persisted synchronously because they are the farmer-facing
result. Rendered imagery is attached afterwards using an independent database
session, so external Process API and object-storage latency never extends the
refresh request.
"""

from __future__ import annotations

import time
import uuid

from arq.connections import RedisSettings, create_pool

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.modules.satellite.service import SatelliteService

logger = get_logger("satellite.jobs")


async def render_satellite_images(
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    raise_on_error: bool = False,
    force: bool = False,
) -> None:
    async with SessionLocal() as session:
        try:
            attached = await SatelliteService(session).render_images(
                user_id, session_id, force=force
            )
            await session.commit()
            logger.info(
                "satellite image enrichment complete: session=%s images=%s",
                session_id,
                attached,
            )
        except Exception:  # numeric session is already durable
            await session.rollback()
            logger.exception("satellite image enrichment failed: session=%s", session_id)
            if raise_on_error:
                raise


async def enqueue_satellite_image_render(
    session_id: uuid.UUID, user_id: uuid.UUID, *, force: bool = False
) -> bool:
    """Persist an image-render job in Redis for the dedicated ARQ worker.

    UUIDs are serialized as strings so the Redis payload remains portable across
    deployments.  ``False`` lets the API retain its best-effort local fallback
    during a short Redis outage without hiding the failure from logs.
    """
    redis = None
    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        job = await redis.enqueue_job(
            "render_satellite_images_job",
            str(session_id),
            str(user_id),
            force,
            # A one-minute bucket is a distributed cooldown: repeated taps cannot
            # fan out costly renders, while a completed/failed job is retryable in
            # the next window instead of being blocked by ARQ result retention.
            _job_id=(
                f"satellite-images-repair:{session_id}:{int(time.time() // 60)}"
                if force
                else f"satellite-images:{session_id}"
            ),
        )
        if job is None:
            logger.info("satellite image job already queued: session=%s", session_id)
        return True
    except Exception:
        logger.exception("could not enqueue satellite image job: session=%s", session_id)
        return False
    finally:
        if redis is not None:
            await redis.close()
