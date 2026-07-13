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

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.logging import get_logger
from app.core.security import ensure_firebase_app
from app.modules.notifications.constants import (
    NOTIFICATION_PROVIDER,
    DeliveryChannel,
    DeliveryStatus,
)

logger = get_logger("notifications.provider")

# Async token lookup by user id (str) → active FCM tokens.
TokenLookup = Callable[[str], Awaitable[list[str]]]

# Coarse Tamil-first + English push titles per module. Precise per-event text is
# rendered by the app from the localization keys carried in the message ``data``;
# these give the OS something bilingual to show even if the app is killed.
PUSH_TITLES: dict[str, tuple[str, str]] = {
    "weather": ("வானிலை எச்சரிக்கை", "Weather alert"),
    "disease": ("நோய் கண்டறிதல்", "Disease result"),
    "market": ("சந்தை விலை", "Market price"),
    "calendar": ("பயிர் நாட்காட்டி", "Crop calendar"),
    "experts": ("நிபுணர் பதில்", "Expert reply"),
    "schemes": ("அரசு திட்டம்", "Govt scheme"),
    "intelligence": ("பண்ணை ஆரோக்கியம்", "Farm health"),
}
DEFAULT_PUSH_TITLE = ("AgrowAI அறிவிப்பு", "AgrowAI update")
PUSH_BODY = "புதிய அறிவிப்பு உள்ளது. / You have a new update."


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


def _push_data(request: DeliveryRequest) -> dict[str, str]:
    """FCM ``data`` must be all-strings; carries the localization keys + route the
    app uses to render (Tamil-first) and deep-link. No user text is put here."""
    return {
        "notification_id": request.notification_id,
        "module": request.module,
        "event_type": request.event_type,
        "title_key": request.title_key,
        "message_key": request.message_key,
        "severity": request.severity,
        "priority": request.priority,
        "action_route": request.action_route or "",
    }


class FCMProvider:
    """Firebase Cloud Messaging push delivery (docs: MASTER_SPEC → FCM).

    In-app delivery is an immediate success (the row is already persisted). For
    the ``push`` channel it looks up the farmer's active device tokens and sends
    one multicast message with a bilingual (ta/en) OS notification plus a data
    payload the app localizes and deep-links from. It never claims a delivery it
    cannot prove: no registered device → ``skipped``; send error or zero
    accepted → ``failed``. Other channels are ``skipped`` (not configured here).

    ``messaging`` is injectable so the sender is unit-tested without Firebase.
    """

    name = "fcm"

    def __init__(
        self, token_lookup: TokenLookup, *, messaging: Any | None = None
    ) -> None:
        self._token_lookup = token_lookup
        self._messaging = messaging

    def _fcm(self) -> Any:
        if self._messaging is not None:
            return self._messaging
        from firebase_admin import messaging  # lazy — only when actually pushing

        return messaging

    async def deliver(
        self, request: DeliveryRequest, *, channels: tuple[str, ...]
    ) -> list[DeliveryResult]:
        results: list[DeliveryResult] = []
        for channel in channels:
            if channel == DeliveryChannel.IN_APP.value:
                results.append(
                    DeliveryResult(
                        channel=channel,
                        status=DeliveryStatus.DELIVERED.value,
                        detail="Shown in the notification center.",
                    )
                )
            elif channel == DeliveryChannel.PUSH.value:
                results.append(await self._push(request))
            else:
                results.append(
                    DeliveryResult(
                        channel=channel,
                        status=DeliveryStatus.SKIPPED.value,
                        detail="Channel not configured.",
                    )
                )
        return results

    async def _push(self, request: DeliveryRequest) -> DeliveryResult:
        tokens = await self._token_lookup(request.user_id)
        if not tokens:
            return DeliveryResult(
                channel=DeliveryChannel.PUSH.value,
                status=DeliveryStatus.SKIPPED.value,
                detail="No registered device.",
            )
        title_ta, title_en = PUSH_TITLES.get(request.module, DEFAULT_PUSH_TITLE)
        messaging = self._fcm()
        message = messaging.MulticastMessage(
            tokens=list(tokens),
            notification=messaging.Notification(
                title=f"{title_ta} / {title_en}", body=PUSH_BODY
            ),
            data=_push_data(request),
        )
        try:
            # firebase-admin's sender is synchronous — keep it off the event loop.
            response = await asyncio.to_thread(
                messaging.send_each_for_multicast, message
            )
        except Exception as exc:  # noqa: BLE001 — never fabricate a delivery
            logger.warning(
                "FCM push failed for notification %s: %s",
                request.notification_id,
                type(exc).__name__,
            )
            return DeliveryResult(
                channel=DeliveryChannel.PUSH.value,
                status=DeliveryStatus.FAILED.value,
                detail="Push send failed.",
            )
        success_count = int(getattr(response, "success_count", 0) or 0)
        if success_count > 0:
            return DeliveryResult(
                channel=DeliveryChannel.PUSH.value,
                status=DeliveryStatus.DELIVERED.value,
                detail=f"Pushed to {success_count}/{len(tokens)} device(s).",
            )
        return DeliveryResult(
            channel=DeliveryChannel.PUSH.value,
            status=DeliveryStatus.FAILED.value,
            detail="No device accepted the push.",
        )


def get_default_provider(
    token_lookup: TokenLookup | None = None,
) -> NotificationProvider:
    """Select the configured provider. ``NOTIFICATION_PROVIDER=fcm`` enables real
    push (Firebase Admin); anything else — or FCM misconfigured — is the honest
    in-app-only mock (never a silent fake send)."""
    if NOTIFICATION_PROVIDER == "fcm":
        if ensure_firebase_app() is None:
            logger.warning(
                "NOTIFICATION_PROVIDER=fcm but Firebase is not configured; "
                "delivering in-app only."
            )
            return MockNotificationProvider()
        if token_lookup is None:
            logger.warning(
                "FCM provider needs a device-token lookup; delivering in-app only."
            )
            return MockNotificationProvider()
        return FCMProvider(token_lookup)
    if NOTIFICATION_PROVIDER:
        logger.info(
            "notification provider '%s' requested but not wired; using mock",
            NOTIFICATION_PROVIDER,
        )
    return MockNotificationProvider()
