"""Health & readiness endpoints (docs/DEPLOYMENT.md → Health Checks)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.logging import get_logger
from app.schemas.response import success

logger = get_logger("health")
router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness — always fast, no dependencies."""
    return success({"status": "ok"}, message="Service healthy")


@router.get("/health/ready")
async def readiness(session: Annotated[AsyncSession, Depends(get_session)]):
    """Readiness — verifies the database connection."""
    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        logger.warning("Readiness DB check failed.")
        db_ok = False
    return success({"database": "ok" if db_ok else "unavailable"})
