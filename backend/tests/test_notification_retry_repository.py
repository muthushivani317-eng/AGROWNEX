"""Retry-queue regression tests, including PostgreSQL JSON safety."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.modules.auth.models import User
from app.modules.notifications.jobs import retry_failed_notifications
from app.modules.notifications.models import Notification, NotificationDeliveryLog
from app.modules.notifications.provider import DeliveryRequest, DeliveryResult
from app.modules.notifications.repository import NotificationRepository
from sqlalchemy.dialects import postgresql


async def _user(db_session, suffix: str) -> User:
    row = User(firebase_uid=f"fb-retry-repo-{suffix}", status="active")
    db_session.add(row)
    await db_session.flush()
    return row


async def _notification(
    db_session,
    user: User,
    *,
    attempts: int = 1,
    log_status: str = "failed",
    payload: dict | None = None,
    delivered_at: datetime | None = None,
    dismissed: bool = False,
    expires_at: datetime | None = None,
) -> Notification:
    row = Notification(
        user_id=user.id,
        module="weather",
        event_type="heavy_rain",
        title_key="t",
        message_key="m",
        severity="warning",
        priority="high",
        dedup_key=f"retry-{uuid.uuid4()}",
        payload_json=payload,
        delivered_at=delivered_at,
        dismissed=dismissed,
        expires_at=expires_at,
    )
    db_session.add(row)
    await db_session.flush()
    for _ in range(attempts):
        db_session.add(
            NotificationDeliveryLog(
                notification_id=row.id, channel="push", status=log_status
            )
        )
    await db_session.flush()
    return row


async def test_multiple_failed_logs_return_one_notification(db_session):
    user = await _user(db_session, "dedup")
    expected = await _notification(db_session, user, attempts=2)
    rows = await NotificationRepository(db_session).list_retryable(
        now=datetime.now(UTC), max_attempts=3
    )
    assert [row.id for row in rows] == [expected.id]


async def test_nested_json_payload_is_retryable(db_session):
    user = await _user(db_session, "json")
    nested = {"farm": {"alerts": [{"code": "rain", "values": [1, 2]}]}}
    expected = await _notification(db_session, user, payload=nested)
    rows = await NotificationRepository(db_session).list_retryable(now=datetime.now(UTC))
    assert [row.id for row in rows] == [expected.id]
    assert rows[0].payload_json == nested


async def test_delivered_dismissed_and_expired_are_excluded(db_session):
    now = datetime.now(UTC)
    user = await _user(db_session, "states")
    await _notification(db_session, user, delivered_at=now)
    await _notification(db_session, user, dismissed=True)
    await _notification(db_session, user, expires_at=now - timedelta(seconds=1))
    assert await NotificationRepository(db_session).list_retryable(now=now) == []


async def test_non_failed_logs_are_excluded(db_session):
    user = await _user(db_session, "nonfailed")
    await _notification(db_session, user, log_status="skipped")
    assert await NotificationRepository(db_session).list_retryable(
        now=datetime.now(UTC)
    ) == []


async def test_max_attempts_are_preserved(db_session):
    user = await _user(db_session, "cap")
    await _notification(db_session, user, attempts=3)
    assert await NotificationRepository(db_session).list_retryable(
        now=datetime.now(UTC), max_attempts=3
    ) == []


async def test_result_limit_is_preserved(db_session):
    user = await _user(db_session, "limit")
    for _ in range(3):
        await _notification(db_session, user)
    rows = await NotificationRepository(db_session).list_retryable(
        now=datetime.now(UTC), limit=2
    )
    assert len(rows) == 2
    assert len({row.id for row in rows}) == 2


class _EmptyScalars:
    def all(self):
        return []


class _EmptyResult:
    def scalars(self):
        return _EmptyScalars()


class _RecordingSession:
    statement = None

    async def execute(self, statement):
        self.statement = statement
        return _EmptyResult()


async def test_postgresql_query_uses_exists_without_entity_distinct():
    session = _RecordingSession()
    await NotificationRepository(session).list_retryable(now=datetime.now(UTC))
    sql = str(
        session.statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).upper()
    assert "EXISTS" in sql
    assert "SELECT DISTINCT" not in sql
    assert "CAST(" not in sql


class _RecoveringProvider:
    name = "recovering"

    def __init__(self) -> None:
        self.requests: list[DeliveryRequest] = []

    async def deliver(self, request: DeliveryRequest, *, channels):
        self.requests.append(request)
        return [DeliveryResult(channel=channel, status="delivered") for channel in channels]


async def test_retry_worker_handles_duplicate_logs_and_nested_json(db_session):
    user = await _user(db_session, "worker")
    nested = {"weather": {"codes": ["heavy_rain.expected"]}}
    await _notification(db_session, user, attempts=2, payload=nested)
    provider = _RecoveringProvider()
    result = await retry_failed_notifications(
        db_session, provider=provider, max_retries=3, now=datetime.now(UTC)
    )
    assert result == {"retried": 1, "delivered": 1}
    assert len(provider.requests) == 1
    assert provider.requests[0].payload == nested
