"""Notification delivery providers (docs: provider abstraction; MASTER_SPEC → FCM).

``NotificationProvider`` is the seam that lets a stored notification be pushed
through an external channel (Firebase Cloud Messaging, OneSignal, SMS, WhatsApp,
Email, Voice) **with no change to the service, API or frontend**. V1 ships a
``MockNotificationProvider`` that "delivers" in-app only (the notification is
already persisted, so the Notification Center shows it immediately) and logs the
attempt. Future providers implement the same Protocol and are selected in
``get_default_provider`` via ``NOTIFICATION_PROVIDER``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.logging import get_logger
from app.modules.notifications.constants import (
    NOTIFICATION_PROVIDER,
    DeliveryChannel,
    DeliveryStatus,
)

logger = get_logger("notifications.provider")


@dataclass(frozen=True)
class DeliveryRequest:
    """The source-agnostic view of a notification handed to a channel."""

    notification_id: str
    user_id: str
    module: str
    event_type: str
    title_key: str
    message_key: str
    severity: str
    priority: str
    payload: dict
    action_route: str | None


@dataclass(frozen=True)
class DeliveryResult:
    """A channel's outcome for one delivery attempt (audited)."""

    channel: str
    status: str
    detail: str | None = None


class NotificationProvider(Protocol):
    """Delivers a stored notification through one or more external channels."""

    name: str

    async def deliver(
        self, request: DeliveryRequest, *, channels: tuple[str, ...]
    ) -> list[DeliveryResult]: ...


class MockNotificationProvider:
    """In-app-only delivery. The notification row already exists, so the client
    renders it; external channels are marked skipped until a real provider is wired."""

    name = "mock"

    async def deliver(
        self, request: DeliveryRequest, *, channels: tuple[str, ...]
    ) -> list[DeliveryResult]:
        results: list[DeliveryResult] = []
        for channel in channels:
            if channel == DeliveryChannel.IN_APP.value:
                logger.info(
                    "notification %s delivered in-app (%s/%s)",
                    request.notification_id,
                    request.module,
                    request.event_type,
                )
                results.append(
                    DeliveryResult(
                        channel=channel,
                        status=DeliveryStatus.DELIVERED.value,
                        detail="Shown in the notification center.",
                    )
                )
            else:
                # No external channel configured in V1 — never silently claim sent.
                results.append(
                    DeliveryResult(
                        channel=channel,
                        status=DeliveryStatus.SKIPPED.value,
                        detail="Channel not configured.",
                    )
                )
        return results


def get_default_provider() -> NotificationProvider:
    """Select the configured provider (mock until FCM/OneSignal/etc. is wired)."""
    # Future: dispatch on NOTIFICATION_PROVIDER → FCM / OneSignal / SMS / …
    if NOTIFICATION_PROVIDER:
        logger.info(
            "notification provider '%s' requested but not wired; using mock",
            NOTIFICATION_PROVIDER,
        )
    return MockNotificationProvider()
