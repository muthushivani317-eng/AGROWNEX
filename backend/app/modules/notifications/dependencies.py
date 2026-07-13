"""Notification dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.notifications.service import NotificationService

__all__ = ["CurrentUser", "NotificationServiceDep"]


def get_notification_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NotificationService:
    return NotificationService(session)


NotificationServiceDep = Annotated[
    NotificationService, Depends(get_notification_service)
]
