"""Integration tests for the notification service: deterministic generation from
real module data, dedup, preference gating, the future queue, delivery audit and
the read/dismiss lifecycle (in-memory DB, weather disabled, fixed 'now')."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from app.modules.auth.models import User
from app.modules.disease.models import DiseaseReport
from app.modules.farms.models import Farm, FarmLocation
from app.modules.market.models import MarketFavourite
from app.modules.market.provider import ProviderPrice
from app.modules.market.repository import MarketRepository
from app.modules.notifications.exceptions import NotificationNotFoundError
from app.modules.notifications.models import (
    FutureNotificationQueue,
    NotificationDeliveryLog,
    NotificationTemplate,
)
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import (
    NotificationOut,
    NotificationPreferencesUpdate,
)
from app.modules.notifications.service import NotificationService
from app.modules.produce.constants import ProduceUnit
from app.modules.produce.schemas import ProduceOfferCreate
from app.modules.produce.service import ProduceService
from sqlalchemy import select

NOW = datetime(2026, 7, 11, 6, 0, tzinfo=UTC)
TODAY = date(2026, 7, 11)


async def _make_user(db_session, uid: str = "fb-notif") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(db_session, user, *, district="Thanjavur") -> Farm:
    farm = Farm(user_id=user.id, name="Field A")
    db_session.add(farm)
    await db_session.flush()
    farm.location = FarmLocation(
        farm_id=farm.id, district=district, block="Block-1", village="Village-1"
    )
    await db_session.flush()
    return farm


def _service(db_session, **kwargs) -> NotificationService:
    return NotificationService(
        db_session, now=NOW, enable_weather=False, **kwargs
    )


async def _add_produce(db_session, user, farm, *, days: int = 3) -> None:
    service = ProduceService(db_session, today=TODAY)
    await service.create_offer(
        user,
        ProduceOfferCreate(
            farm_id=farm.id,
            crop_name="Paddy",
            quantity=10.0,
            unit=ProduceUnit.QUINTAL,
            expected_harvest_date=TODAY + timedelta(days=days),
        ),
    )


async def _add_disease(db_session, user, farm, *, confidence: int = 95) -> DiseaseReport:
    report = DiseaseReport(
        user_id=user.id,
        farm_id=farm.id,
        image_url="https://r2/a.jpg",
        crop="Paddy",
        disease="Blast",
        confidence=confidence,
        needs_expert_review=False,
    )
    db_session.add(report)
    await db_session.flush()
    return report


# --------------------------------------------------------------------------- #
# Seeding + generation
# --------------------------------------------------------------------------- #
async def test_sync_seeds_templates(db_session) -> None:
    user = await _make_user(db_session)
    await _service(db_session).sync(user)
    templates = (await db_session.execute(select(NotificationTemplate))).scalars().all()
    # One template per rule (all 24 event types).
    assert len(templates) >= 24


async def test_sync_generates_produce_notification(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_produce(db_session, user, farm, days=3)

    service = _service(db_session)
    await service.sync(user)

    page = await service.list_notifications(user, module="produce", sync=False)
    assert page.total == 2
    assert {item.event_type for item in page.items} == {
        "offer_submitted",
        "harvest_approaching",
    }
    assert all(item.action_route.startswith("/produce/") for item in page.items)


async def test_sync_is_deduplicated(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_disease(db_session, user, farm)

    service = _service(db_session)
    await service.sync(user)
    first = await service.list_notifications(user, module="disease", sync=False)
    assert first.total == 1

    # A second pass creates nothing new for the same event.
    created = await service.sync(user)
    second = await service.list_notifications(user, module="disease", sync=False)
    assert second.total == 1
    assert created == 0


async def test_disease_high_confidence_notification(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_disease(db_session, user, farm, confidence=95)
    service = _service(db_session)
    await service.sync(user)
    page = await service.list_notifications(user, module="disease", sync=False)
    assert page.items[0].event_type == "high_confidence_disease"
    assert page.items[0].severity == "critical"


async def test_market_favourite_alert(db_session) -> None:
    user = await _make_user(db_session)
    mrepo = MarketRepository(db_session)
    await mrepo.save_prices(
        [
            ProviderPrice(
                commodity="Paddy",
                variety="Common",
                market="Thanjavur Mandi",
                district="Thanjavur",
                state="Tamil Nadu",
                minimum_price=1900,
                maximum_price=2100,
                modal_price=2000,
                unit="quintal",
                price_date=TODAY,
                source="agmarknet",
            )
        ]
    )
    db_session.add(
        MarketFavourite(
            user_id=user.id,
            commodity="Paddy",
            market_name="Thanjavur Mandi",
            district="Thanjavur",
            state="Tamil Nadu",
        )
    )
    await db_session.flush()

    service = _service(db_session)
    await service.sync(user)
    page = await service.list_notifications(user, module="market", sync=False)
    assert page.total == 2
    assert {item.event_type for item in page.items} == {
        "favourite_crop_alert",
        "price_peak",
    }


# --------------------------------------------------------------------------- #
# Preference gating
# --------------------------------------------------------------------------- #
async def test_module_preference_gate(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_produce(db_session, user, farm, days=3)

    service = _service(db_session)
    await service.update_preferences(
        user, NotificationPreferencesUpdate(produce_enabled=False)
    )
    await service.sync(user)
    page = await service.list_notifications(user, module="produce", sync=False)
    assert page.total == 0  # produce muted → no notification generated


async def test_min_severity_gate(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_produce(db_session, user, farm, days=3)  # harvest_approaching = info

    service = _service(db_session)
    await service.update_preferences(
        user, NotificationPreferencesUpdate(min_severity="critical")
    )
    await service.sync(user)
    page = await service.list_notifications(user, module="produce", sync=False)
    assert page.total == 0  # info below the critical gate


# --------------------------------------------------------------------------- #
# Future queue promotion
# --------------------------------------------------------------------------- #
async def test_due_queue_is_promoted(db_session) -> None:
    user = await _make_user(db_session)
    repo = NotificationRepository(db_session)
    db_session.add(
        FutureNotificationQueue(
            user_id=user.id,
            module="schemes",
            event_type="application_closing",
            title_key="notifications.rules.schemes.application_closing.title",
            message_key="notifications.rules.schemes.application_closing.message",
            payload_json={"scheme_id": "x"},
            severity="warning",
            priority="high",
            action_route="/schemes/x",
            dedup_key="schemes:application_closing:queued-due",
            scheduled_for=NOW - timedelta(days=1),
        )
    )
    await db_session.flush()

    await _service(db_session).sync(user)
    promoted = await repo.get_by_dedup(user.id, "schemes:application_closing:queued-due")
    assert promoted is not None
    assert promoted.delivered_at is not None  # delivered on promotion


async def test_future_queue_not_promoted_early(db_session) -> None:
    user = await _make_user(db_session)
    repo = NotificationRepository(db_session)
    db_session.add(
        FutureNotificationQueue(
            user_id=user.id,
            module="schemes",
            event_type="application_closing",
            title_key="notifications.rules.schemes.application_closing.title",
            message_key="notifications.rules.schemes.application_closing.message",
            payload_json={},
            severity="warning",
            priority="high",
            action_route="/schemes/x",
            dedup_key="schemes:application_closing:queued-future",
            scheduled_for=NOW + timedelta(days=10),
        )
    )
    await db_session.flush()

    await _service(db_session).sync(user)
    assert (
        await repo.get_by_dedup(user.id, "schemes:application_closing:queued-future")
        is None
    )


# --------------------------------------------------------------------------- #
# Read / dismiss lifecycle + unread badge
# --------------------------------------------------------------------------- #
async def test_mark_read_and_unread_count(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_produce(db_session, user, farm, days=3)
    await _add_disease(db_session, user, farm)

    service = _service(db_session)
    # Mute the scheme-eligibility source so this test isolates produce + disease.
    await service.update_preferences(
        user, NotificationPreferencesUpdate(scheme_enabled=False)
    )
    assert await service.unread_count(user) == 3

    page = await service.list_notifications(user, sync=False)
    first = page.items[0]
    await service.mark_read(user, first.id)
    assert await service.unread_count(user, sync=False) == 2

    updated = await service.mark_all_read(user)
    assert updated == 2
    assert await service.unread_count(user, sync=False) == 0


async def test_dismiss_hides_notification(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_produce(db_session, user, farm, days=3)

    service = _service(db_session)
    await service.sync(user)
    page = await service.list_notifications(user, module="produce", sync=False)
    target = page.items[0]
    await service.dismiss(user, target.id)

    after = await service.list_notifications(user, module="produce", sync=False)
    assert after.total == 1


async def test_mark_read_requires_ownership(db_session) -> None:
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    farm = await _make_farm(db_session, owner)
    await _add_produce(db_session, owner, farm, days=3)
    service = _service(db_session)
    await service.sync(owner)
    page = await service.list_notifications(owner, sync=False)
    with pytest.raises(NotificationNotFoundError):
        await service.mark_read(other, page.items[0].id)
    with pytest.raises(NotificationNotFoundError):
        await service.dismiss(owner, uuid.uuid4())


# --------------------------------------------------------------------------- #
# Delivery audit
# --------------------------------------------------------------------------- #
async def test_delivery_is_logged(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_produce(db_session, user, farm, days=3)
    await _service(db_session).sync(user)
    logs = (await db_session.execute(select(NotificationDeliveryLog))).scalars().all()
    assert len(logs) >= 1
    assert any(log.channel == "in_app" and log.status == "delivered" for log in logs)


# --------------------------------------------------------------------------- #
# Preferences + mapper
# --------------------------------------------------------------------------- #
async def test_preferences_defaults_and_partial_update(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    prefs = await service.get_preferences(user)
    assert prefs.weather_enabled is True
    assert prefs.min_severity == "info"

    updated = await service.update_preferences(
        user, NotificationPreferencesUpdate(weather_enabled=False, min_severity="warning")
    )
    assert updated.weather_enabled is False
    assert updated.min_severity == "warning"
    assert updated.disease_enabled is True  # untouched


async def test_notification_out_mapper(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await _add_disease(db_session, user, farm)
    service = _service(db_session)
    await service.sync(user)
    page = await service.list_notifications(user, module="disease", sync=False)
    out = NotificationOut.from_model(page.items[0])
    assert out.module == "disease"
    assert out.payload["disease"] == "Blast"
    assert out.read is False
    assert out.title_key.endswith(".title")
