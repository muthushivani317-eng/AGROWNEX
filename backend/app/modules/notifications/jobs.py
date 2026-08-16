"""Notification background jobs (Phase 3 — ARQ worker).

Two scheduled jobs, both pure orchestration over existing service/repository so
they unit-test with mocked providers (no network):

* ``evaluate_weather_alerts`` — runs the deterministic notification sync
  (weather-enabled) for every farmer who owns a farm, so weather alert rules are
  evaluated and notification rows created. Reuses the whole pipeline rather than
  duplicating alert logic.
* ``retry_failed_notifications`` — re-delivers notifications whose last attempt
  failed, capped at ``max_retries`` attempts.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.farms.repositories import FarmRepository
from app.modules.notifications.constants import (
    OUTBREAK_MIN_DISTINCT_FARMS,
    OUTBREAK_WINDOW_DAYS,
)
from app.modules.notifications.models import NotificationDeliveryLog
from app.modules.notifications.provider import (
    DeliveryRequest,
    NotificationProvider,
    get_default_provider,
)
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.service import NotificationService
from app.modules.notifications.sources import NotificationSources

logger = get_logger("notifications.jobs")


async def evaluate_weather_alerts(
    session: AsyncSession,
    *,
    provider: NotificationProvider | None = None,
    sources: NotificationSources | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    effective_now = now or datetime.now(UTC)
    groups = await DiseaseReportRepository(session).district_outbreak_groups(
        since=effective_now - timedelta(days=OUTBREAK_WINDOW_DAYS),
        min_distinct_farms=OUTBREAK_MIN_DISTINCT_FARMS,
    )
    outbreak_index: dict[str, list[tuple[str, str]]] = {}
    for district, crop, disease, _count in groups:
        outbreak_index.setdefault(district, []).append((crop, disease))

    owner_ids = await FarmRepository(session).list_owner_ids()
    users: list[User] = []
    if owner_ids:
        result = await session.execute(select(User).where(User.id.in_(owner_ids)))
        users = list(result.scalars().all())

    run_sources = sources or NotificationSources(
        session,
        now=effective_now,
        enable_weather=True,
        outbreak_index=outbreak_index,
    )
    created = 0
    for user in users:
        service = NotificationService(
            session,
            provider=provider,
            sources=run_sources,
            now=effective_now,
            enable_weather=True,
        )
        created += await service.sync(user)

    logger.info("weather alerts: %s farmers, %s notifications", len(users), created)
    return {"farmers": len(users), "notifications_created": created}


async def retry_failed_notifications(
    session: AsyncSession,
    *,
    provider: NotificationProvider | None = None,
    max_retries: int = 3,
    now: datetime | None = None,
) -> dict[str, int]:
    now = now or datetime.now(UTC)
    provider = provider or get_default_provider()
    repo = NotificationRepository(session)

    retryable = await repo.list_retryable(now=now, max_attempts=max_retries)
    retried = 0
    delivered = 0
    for notification in retryable:
        failed_channels = tuple(
            {d.channel for d in notification.deliveries if d.status == "failed"}
        )
        if not failed_channels:
            continue
        request = DeliveryRequest(
            notification_id=str(notification.id),
            user_id=str(notification.user_id),
            module=notification.module,
            event_type=notification.event_type,
            title_key=notification.title_key,
            message_key=notification.message_key,
            severity=notification.severity,
            priority=notification.priority,
            payload=notification.payload_json or {},
            action_route=notification.action_route,
        )
        results = await provider.deliver(request, channels=failed_channels)
        retried += 1
        for result in results:
            await repo.add_delivery(
                NotificationDeliveryLog(
                    notification_id=notification.id,
                    channel=result.channel,
                    status=result.status,
                    detail=result.detail,
                    sent_at=now,
                    delivered_at=now if result.status == "delivered" else None,
                )
            )
            if result.status == "delivered":
                notification.delivered_at = now
                delivered += 1
    await session.flush()

    logger.info("notification retry: %s retried, %s delivered", retried, delivered)
    return {"retried": retried, "delivered": delivered}
