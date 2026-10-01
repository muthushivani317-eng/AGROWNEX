"""Two first-launch requests racing to create notification preferences (prod 500, 2026-09-30)."""
from __future__ import annotations

from app.modules.auth.models import User
from app.modules.notifications.models import NotificationPreferences
from app.modules.notifications.repository import NotificationRepository


async def test_parallel_create_returns_the_existing_row(db_session):
    user = User(firebase_uid="race-user", status="active")
    db_session.add(user)
    await db_session.flush()
    first = NotificationPreferences(user_id=user.id)
    db_session.add(first)
    await db_session.flush()  # the "other" request won the race

    repo = NotificationRepository(db_session)
    got = await repo.add_preferences(NotificationPreferences(user_id=user.id))

    assert got.id == first.id
    assert await repo.get_preferences(user.id) is first
