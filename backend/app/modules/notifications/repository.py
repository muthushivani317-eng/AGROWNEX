"""Notification repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the notification tables — notifications (owned,
filtered, paginated, deduped), preferences, delivery logs, the seeded template
table and the future queue. No SQL lives in routes or the service.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import (
    DeviceToken,
    FutureNotificationQueue,
    Notification,
    NotificationDeliveryLog,
    NotificationPreferences,
    NotificationTemplate,
)


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Notifications
    # ----------------------------------------------------------------- #
    def _visible(self, user_id: uuid.UUID, *, now: datetime) -> Select[tuple[Notification]]:
        """Owned, not dismissed, not expired, and already due (scheduled ≤ now)."""
        return select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_deleted.is_(False),
            Notification.dismissed.is_(False),
            or_(Notification.expires_at.is_(None), Notification.expires_at > now),
            or_(
                Notification.scheduled_for.is_(None),
                Notification.scheduled_for <= now,
            ),
        )

    async def add(self, notification: Notification) -> Notification:
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get_for_user(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_dedup(
        self, user_id: uuid.UUID, dedup_key: str
    ) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.dedup_key == dedup_key,
            )
        )
        return result.scalar_one_or_none()

    def _filtered(
        self,
        user_id: uuid.UUID,
        *,
        now: datetime,
        module: str | None,
        severity: str | None,
        unread_only: bool,
    ) -> Select[tuple[Notification]]:
        stmt = self._visible(user_id, now=now)
        if module:
            stmt = stmt.where(Notification.module == module)
        if severity:
            stmt = stmt.where(Notification.severity == severity)
        if unread_only:
            stmt = stmt.where(Notification.read.is_(False))
        return stmt

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        now: datetime,
        module: str | None = None,
        severity: str | None = None,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        base = self._filtered(
            user_id,
            now=now,
            module=module,
            severity=severity,
            unread_only=unread_only,
        )
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self.session.execute(
                    base.order_by(Notification.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return list(rows), total

    async def count_unread(self, user_id: uuid.UUID, *, now: datetime) -> int:
        base = self._filtered(
            user_id, now=now, module=None, severity=None, unread_only=True
        )
        return int(
            (
                await self.session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )

    async def mark_all_read(self, user_id: uuid.UUID, *, now: datetime) -> int:
        rows, _ = await self.list_for_user(user_id, now=now, unread_only=True, limit=10_000)
        for row in rows:
            row.read = True
            row.read_at = now
        await self.session.flush()
        return len(rows)

    # ----------------------------------------------------------------- #
    # Preferences
    # ----------------------------------------------------------------- #
    async def get_preferences(
        self, user_id: uuid.UUID
    ) -> NotificationPreferences | None:
        result = await self.session.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def add_preferences(
        self, preferences: NotificationPreferences
    ) -> NotificationPreferences:
        self.session.add(preferences)
        await self.session.flush()
        return preferences

    # ----------------------------------------------------------------- #
    # Delivery log
    # ----------------------------------------------------------------- #
    async def add_delivery(
        self, entry: NotificationDeliveryLog
    ) -> NotificationDeliveryLog:
        self.session.add(entry)
        await self.session.flush()
        return entry

    # ----------------------------------------------------------------- #
    # Device tokens (FCM push)
    # ----------------------------------------------------------------- #
    async def upsert_device_token(
        self, *, user_id: uuid.UUID, token: str, platform: str
    ) -> DeviceToken:
        """Register (or re-activate/re-own) a push token; unique by token."""
        existing = (
            await self.session.execute(
                select(DeviceToken).where(DeviceToken.token == token)
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.user_id = user_id
            existing.platform = platform
            existing.is_active = True
            await self.session.flush()
            return existing
        row = DeviceToken(
            user_id=user_id, token=token, platform=platform, is_active=True
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def deactivate_device_token(
        self, *, user_id: uuid.UUID, token: str
    ) -> bool:
        row = (
            await self.session.execute(
                select(DeviceToken).where(
                    DeviceToken.token == token, DeviceToken.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        row.is_active = False
        await self.session.flush()
        return True

    async def list_active_tokens(self, user_id: uuid.UUID) -> list[str]:
        result = await self.session.execute(
            select(DeviceToken.token).where(
                DeviceToken.user_id == user_id, DeviceToken.is_active.is_(True)
            )
        )
        return [row[0] for row in result.all()]

    async def list_retryable(
        self, *, now: datetime, max_attempts: int = 3, limit: int = 100
    ) -> list[Notification]:
        """Undelivered, non-dismissed, unexpired notifications that have a failed
        delivery attempt — the retry job's queue. Attempt-count is capped by the
        caller using the eager-loaded ``deliveries`` (fewer than ``max_attempts``)."""
        stmt = (
            select(Notification)
            .join(NotificationDeliveryLog)
            .where(
                Notification.delivered_at.is_(None),
                Notification.dismissed.is_(False),
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > now,
                ),
                NotificationDeliveryLog.status == "failed",
            )
            .distinct()
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        candidates = list(result.scalars().unique().all())
        return [n for n in candidates if len(n.deliveries) < max_attempts]

    # ----------------------------------------------------------------- #
    # Templates (seeded rule table)
    # ----------------------------------------------------------------- #
    async def template_exists(self, module: str, event_type: str) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(NotificationTemplate)
            .where(
                NotificationTemplate.module == module,
                NotificationTemplate.event_type == event_type,
            )
        )
        return int(result.scalar_one()) > 0

    async def add_template(
        self, template: NotificationTemplate
    ) -> NotificationTemplate:
        self.session.add(template)
        await self.session.flush()
        return template

    # ----------------------------------------------------------------- #
    # Future queue
    # ----------------------------------------------------------------- #
    async def get_queued_by_dedup(
        self, user_id: uuid.UUID, dedup_key: str
    ) -> FutureNotificationQueue | None:
        result = await self.session.execute(
            select(FutureNotificationQueue).where(
                FutureNotificationQueue.user_id == user_id,
                FutureNotificationQueue.dedup_key == dedup_key,
            )
        )
        return result.scalar_one_or_none()

    async def add_queued(
        self, entry: FutureNotificationQueue
    ) -> FutureNotificationQueue:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_due_queued(
        self, user_id: uuid.UUID, *, now: datetime
    ) -> list[FutureNotificationQueue]:
        result = await self.session.execute(
            select(FutureNotificationQueue).where(
                FutureNotificationQueue.user_id == user_id,
                FutureNotificationQueue.processed.is_(False),
                FutureNotificationQueue.scheduled_for <= now,
            )
        )
        return list(result.scalars().all())
