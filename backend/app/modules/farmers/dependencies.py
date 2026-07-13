"""Farmer dependency injection (docs/BACKEND_ARCHITECTURE.md → Dependency Injection).

Reuses the authenticated-user dependency from the auth module so the current
user is resolved from the Firebase JWT exactly once, app-wide.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.farmers.service import FarmerService

__all__ = ["CurrentUser", "FarmerServiceDep"]


def get_farmer_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FarmerService:
    return FarmerService(session)


FarmerServiceDep = Annotated[FarmerService, Depends(get_farmer_service)]
