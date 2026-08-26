"""Broadcast delivery provider (docs: reuse the Notification engine; provider seam).

Broadcasts are delivered by creating real notifications for the targeted farmers —
reusing the Notifications module (no duplicate delivery code). The provider is an
abstraction so future channels (FCM push, SMS, WhatsApp, Email) plug in with no change
to the admin service (docs: FUTURE READY). ``MockBroadcastProvider`` is used in tests.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.models import BroadcastMessage


class BroadcastProvider(Protocol):
    async def deliver(
        self,
        session: AsyncSession,
        broadcast: BroadcastMessage,
        recipient_ids: list[uuid.UUID],
    ) -> int:
        """Deliver the broadcast to the recipients; return the delivered count."""
        ...


class NotificationBroadcastProvider:
    """Delivers a broadcast as an in-app notification per targeted farmer (reused)."""

    async def deliver(
        self,
        session: AsyncSession,
        broadcast: BroadcastMessage,
        recipient_ids: list[uuid.UUID],
    ) -> int:
        from app.modules.notifications.constants import (
            NotificationModule,
            Priority,
            Severity,
        )
        from app.modules.notifications.models import Notification
        from app.modules.notifications.repository import NotificationRepository

        repo = NotificationRepository(session)
        delivered = 0
        for user_id in recipient_ids:
            notification = Notification(
                user_id=user_id,
                module=NotificationModule.SYSTEM.value,
                event_type="broadcast",
                title_key="notifications.broadcast.title",
                message_key="notifications.broadcast.message",
                payload_json={
                    "title": broadcast.title,
                    "body": broadcast.body,
                    "language": broadcast.language,
                },
                severity=Severity.INFO.value,
                priority=Priority.MEDIUM.value,
                action_route="/notifications",
                dedup_key=f"broadcast:{broadcast.id}:{user_id}",
            )
            await repo.add(notification)
            delivered += 1
        return delivered


class MockBroadcastProvider:
    """Acknowledges delivery without writing notifications (tests / dry runs)."""

    def __init__(self) -> None:
        self.calls: list[tuple[uuid.UUID, int]] = []

    async def deliver(
        self,
        session: AsyncSession,
        broadcast: BroadcastMessage,
        recipient_ids: list[uuid.UUID],
    ) -> int:
        self.calls.append((broadcast.id, len(recipient_ids)))
        return len(recipient_ids)


def get_default_broadcast_provider() -> BroadcastProvider:
    return NotificationBroadcastProvider()
