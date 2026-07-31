"""Health & readiness endpoints (docs/DEPLOYMENT.md → Health Checks)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
    from app.modules.disease.ml_runtime import get_model_runtime

    model_ok = not settings.disease_model_required or get_model_runtime().ready
    data = {
        "database": "ok" if db_ok else "unavailable",
        "disease_model": "ok" if model_ok else "unavailable",
    }
    body = success(data).model_dump(mode="json")
    return JSONResponse(status_code=200 if db_ok and model_ok else 503, content=body)
