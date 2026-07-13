"""The Expert Connect ↔ Notification engine reuse: a created consultation surfaces
as a notification through the notification engine's expert source (in-memory DB)."""
from __future__ import annotations

from datetime import UTC, datetime

from app.modules.auth.models import User
from app.modules.experts.provider import MockExpertProvider
from app.modules.experts.schemas import ConsultationCreate
from app.modules.experts.service import ExpertService
from app.modules.notifications.service import NotificationService

NOW = datetime(2026, 7, 11, 6, 0, tzinfo=UTC)


async def _make_user(db_session) -> User:
    user = User(firebase_uid="fb-expnotif", status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def test_assigned_consultation_creates_notification(db_session) -> None:
    user = await _make_user(db_session)
    experts = ExpertService(db_session, provider=MockExpertProvider(), now=NOW)
    await experts.create_consultation(
        user,
        ConsultationCreate(
            subject="Leaf spots on paddy",
            description="Yellow spots spreading on my paddy crop.",
        ),
    )

    notifications = NotificationService(db_session, now=NOW, enable_weather=False)
    await notifications.sync(user)

    page = await notifications.list_notifications(user, module="experts", sync=False)
    assert page.total == 1
    item = page.items[0]
    assert item.event_type == "consultation_assigned"
    assert item.action_route.startswith("/consultations/")


async def test_expert_notification_is_deduplicated(db_session) -> None:
    user = await _make_user(db_session)
    experts = ExpertService(db_session, provider=MockExpertProvider(), now=NOW)
    await experts.create_consultation(
        user,
        ConsultationCreate(
            subject="Irrigation advice", description="How often to irrigate paddy now?"
        ),
    )
    notifications = NotificationService(db_session, now=NOW, enable_weather=False)
    await notifications.sync(user)
    created_again = await notifications.sync(user)  # second pass — no duplicate
    page = await notifications.list_notifications(user, module="experts", sync=False)
    assert page.total == 1
    assert created_again == 0
