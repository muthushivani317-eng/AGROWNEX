"""Push delivery tests (Phase 3 — FCM): device-token storage, the FCM provider's
honest delivery outcomes, and provider selection. No Firebase/network — the
messaging SDK is faked."""
from __future__ import annotations

from app.modules.auth.models import User
from app.modules.notifications import provider as provider_module
from app.modules.notifications.provider import (
    DeliveryRequest,
    FCMProvider,
    MockNotificationProvider,
    get_default_provider,
)
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.service import NotificationService


async def _user(db_session, uid: str = "fb-push") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


def _request(user_id: str, module: str = "weather") -> DeliveryRequest:
    return DeliveryRequest(
        notification_id="n-1",
        user_id=user_id,
        module=module,
        event_type="heavy_rain",
        title_key="notifications.rules.weather.heavy_rain.title",
        message_key="notifications.rules.weather.heavy_rain.message",
        severity="warning",
        priority="high",
        payload={"mm": 80},
        action_route="/weather",
    )


# --------------------------------------------------------------------------- #
# Fake firebase_admin.messaging
# --------------------------------------------------------------------------- #
class _Notification:
    def __init__(self, title, body):
        self.title = title
        self.body = body


class _Multicast:
    def __init__(self, tokens, notification, data):
        self.tokens = tokens
        self.notification = notification
        self.data = data


class _Response:
    def __init__(self, success_count):
        self.success_count = success_count


class FakeMessaging:
    def __init__(self, *, success_count: int = 1, raise_exc: Exception | None = None):
        self.success_count = success_count
        self.raise_exc = raise_exc
        self.sent: list[_Multicast] = []

    def Notification(self, *, title, body):  # noqa: N802 — mirrors SDK API
        return _Notification(title, body)

    def MulticastMessage(self, *, tokens, notification, data):  # noqa: N802
        return _Multicast(tokens, notification, data)

    def send_each_for_multicast(self, message):
        if self.raise_exc is not None:
            raise self.raise_exc
        self.sent.append(message)
        return _Response(self.success_count)


# --------------------------------------------------------------------------- #
# Device-token repository
# --------------------------------------------------------------------------- #
async def test_device_token_upsert_reactivate_and_list(db_session):
    user = await _user(db_session, "fb-token")
    repo = NotificationRepository(db_session)

    d1 = await repo.upsert_device_token(user_id=user.id, token="tok-a", platform="android")
    assert d1.is_active is True
    assert await repo.list_active_tokens(user.id) == ["tok-a"]

    # Re-registering the same token is idempotent (no duplicate row).
    d2 = await repo.upsert_device_token(user_id=user.id, token="tok-a", platform="ios")
    assert d2.id == d1.id
    assert d2.platform == "ios"
    assert await repo.list_active_tokens(user.id) == ["tok-a"]

    # Deactivation drops it from the active set.
    assert await repo.deactivate_device_token(user_id=user.id, token="tok-a") is True
    assert await repo.list_active_tokens(user.id) == []
    # Unknown token → False, no error.
    assert await repo.deactivate_device_token(user_id=user.id, token="nope") is False


async def test_service_register_and_unregister_device(db_session):
    user = await _user(db_session, "fb-svc-token")
    service = NotificationService(db_session)

    device = await service.register_device(user, token="tok-b", platform="android")
    assert device.is_active is True
    assert await NotificationRepository(db_session).list_active_tokens(user.id) == ["tok-b"]

    assert await service.unregister_device(user, token="tok-b") is True
    assert await NotificationRepository(db_session).list_active_tokens(user.id) == []


# --------------------------------------------------------------------------- #
# FCMProvider.deliver — honest outcomes
# --------------------------------------------------------------------------- #
async def _lookup(tokens):
    async def _inner(_user_id: str) -> list[str]:
        return list(tokens)

    return _inner


async def test_fcm_push_delivered_when_tokens_and_send_succeeds():
    fake = FakeMessaging(success_count=2)
    fcm = FCMProvider(await _lookup(["t1", "t2"]), messaging=fake)

    results = await fcm.deliver(_request("u1"), channels=("in_app", "push"))
    by_channel = {r.channel: r for r in results}

    assert by_channel["in_app"].status == "delivered"
    assert by_channel["push"].status == "delivered"
    # The message carried the bilingual title + deep-link data (localization keys).
    assert len(fake.sent) == 1
    msg = fake.sent[0]
    assert "வானிலை" in msg.notification.title and "Weather" in msg.notification.title
    assert msg.data["action_route"] == "/weather"
    assert msg.data["notification_id"] == "n-1"
    assert set(msg.tokens) == {"t1", "t2"}


async def test_fcm_push_skipped_when_no_device():
    fake = FakeMessaging()
    fcm = FCMProvider(await _lookup([]), messaging=fake)

    results = await fcm.deliver(_request("u1"), channels=("push",))
    assert results[0].status == "skipped"
    assert fake.sent == []  # never called the SDK with nothing to send


async def test_fcm_push_failed_when_no_device_accepts():
    fake = FakeMessaging(success_count=0)
    fcm = FCMProvider(await _lookup(["t1"]), messaging=fake)

    results = await fcm.deliver(_request("u1"), channels=("push",))
    assert results[0].status == "failed"


async def test_fcm_push_failed_on_send_error_never_fabricates():
    fake = FakeMessaging(raise_exc=RuntimeError("fcm down"))
    fcm = FCMProvider(await _lookup(["t1"]), messaging=fake)

    results = await fcm.deliver(_request("u1"), channels=("push",))
    assert results[0].status == "failed"


async def test_fcm_unknown_channel_is_skipped():
    fcm = FCMProvider(await _lookup(["t1"]), messaging=FakeMessaging())
    results = await fcm.deliver(_request("u1"), channels=("sms",))
    assert results[0].status == "skipped"


# --------------------------------------------------------------------------- #
# Provider selection
# --------------------------------------------------------------------------- #
async def test_default_provider_is_mock():
    assert isinstance(get_default_provider(), MockNotificationProvider)


async def test_fcm_selected_when_configured(monkeypatch):
    monkeypatch.setattr(provider_module, "NOTIFICATION_PROVIDER", "fcm")
    monkeypatch.setattr(provider_module, "ensure_firebase_app", lambda: object())

    async def lookup(_uid):
        return []

    assert isinstance(get_default_provider(token_lookup=lookup), FCMProvider)


async def test_fcm_falls_back_to_mock_when_firebase_unconfigured(monkeypatch):
    monkeypatch.setattr(provider_module, "NOTIFICATION_PROVIDER", "fcm")
    monkeypatch.setattr(provider_module, "ensure_firebase_app", lambda: None)

    async def lookup(_uid):
        return []

    # No silent fake: FCM requested but unconfigured → honest in-app mock.
    assert isinstance(
        get_default_provider(token_lookup=lookup), MockNotificationProvider
    )


async def test_fcm_falls_back_to_mock_without_token_lookup(monkeypatch):
    monkeypatch.setattr(provider_module, "NOTIFICATION_PROVIDER", "fcm")
    monkeypatch.setattr(provider_module, "ensure_firebase_app", lambda: object())
    assert isinstance(get_default_provider(), MockNotificationProvider)
