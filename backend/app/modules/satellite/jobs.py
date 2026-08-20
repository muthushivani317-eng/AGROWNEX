"""Best-effort satellite enrichment jobs.

Numeric indices are persisted synchronously because they are the farmer-facing
result. Rendered imagery is attached afterwards using an independent database
session, so external Process API and object-storage latency never extends the
refresh request.
"""

from __future__ import annotations

import uuid

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.modules.satellite.service import SatelliteService

logger = get_logger("satellite.jobs")


async def render_satellite_images(session_id: uuid.UUID, user_id: uuid.UUID) -> None:
    async with SessionLocal() as session:
        try:
            attached = await SatelliteService(session).render_images(user_id, session_id)
            await session.commit()
            logger.info(
                "satellite image enrichment complete: session=%s images=%s",
                session_id,
                attached,
            )
        except Exception:  # best effort: numeric session is already durable
            await session.rollback()
            logger.exception("satellite image enrichment failed: session=%s", session_id)
