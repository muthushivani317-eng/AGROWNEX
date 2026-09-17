"""Integration tests for the calendar service (in-memory DB, fake weather)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from tests.weather_fixture import build_raw

from app.core.timezone import today_ist
from app.modules.auth.models import User
from app.modules.calendar.constants import EventStatus, WeatherAdvisory, WeatherDependency
from app.modules.calendar.exceptions import (
    CalendarEventNotFoundError,
    FarmCalendarContextMismatchError,
    FarmNotFoundError,
    SowingDateRequiredError,
)
from app.modules.calendar.registry import CropStageRegistry, schedule_hash
from app.modules.calendar.schedules import DEFAULT_SCHEDULE
from app.modules.calendar.schemas import (
    GenerateCalendarRequest,
    UpdateCalendarEventRequest,
)
from app.modules.calendar.service import CalendarService
from app.modules.farms.models import Farm, FarmLocation
from app.modules.notifications.sources import NotificationSources
from app.modules.weather.cache import WeatherCache
from app.modules.weather.service import WeatherService


class FakeProvider:
    def __init__(self, raw: dict) -> None:
        self.raw = raw

    async def fetch(self, latitude: float, longitude: float) -> dict:
        return self.raw


def _heavy_rain_raw() -> dict:
    raw = build_raw()
    n = len(raw["hourly"]["time"])
    raw["hourly"]["precipitation"] = [6.0] * n  # ~144 mm/24h → severe rain insight
    raw["hourly"]["precipitation_probability"] = [95] * n
    return raw


def _today() -> date:
    # Match CalendarService's day-boundary (IST, not UTC) — see
    # app.core.timezone for why plain datetime.now(UTC).date() is wrong here.
    return today_ist()


async def _make_user(db_session, uid: str = "fb-cal-1") -> User:
    user = User(
        firebase_uid=uid,
        phone_number="+919876500000",
        email=None,
        is_phone_verified=True,
        is_email_verified=False,
        status="active",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(
    db_session,
    user: User,
    *,
    crop: str | None = "wheat",
    sowing_date: date | None = None,
    irrigation_type: str | None = "drip",
    with_location: bool = True,
) -> Farm:
    farm = Farm(
        user_id=user.id,
        name="North Field",
        crop=crop,
        sowing_date=sowing_date if sowing_date is not None else _today(),
        irrigation_type=irrigation_type,
    )
    db_session.add(farm)
    await db_session.flush()
    if with_location:
        db_session.add(FarmLocation(farm_id=farm.id, latitude=9.9, longitude=78.1, source="gps"))
        await db_session.flush()
    return farm


def _service(db_session, *, raw: dict | None = None) -> CalendarService:
    weather = WeatherService(
        db_session, provider=FakeProvider(raw or build_raw()), cache=WeatherCache()
    )
    activities = [
        {
            "code": item.code,
            "activity_type": item.activity_type.value,
            "label_key": f"calendar.verified.test.{item.code}.title",
            "description_key": f"calendar.verified.test.{item.code}.description",
            "day_offset": item.day_offset,
            "notification_offset_days": 1 if item.reminder_enabled else None,
            "notification_eligible": item.reminder_enabled,
            "priority": item.priority.value,
            "weather_dependency": item.weather_dependency.value,
        }
        for item in DEFAULT_SCHEDULE
    ]
    entry = {
        "schema_version": "1.0",
        "canonical_crop_id": "wheat",
        "aliases": [],
        "variety_or_duration_group": "test_only",
        "stages": [
            {
                "code": "test_stage",
                "label_key": "calendar.stages.test",
                "start_offset": 0,
                "end_offset": 150,
                "activities": activities,
            }
        ],
        "geographic_limitations": ["test"],
        "season_limitations": ["test"],
        "source_organization": "Test fixture only",
        "document_reference": "TEST-ONLY",
        "reviewer": "Test fixture",
        "approval_date": _today().isoformat(),
        "review_date": date(2099, 1, 1).isoformat(),
        "version": "test-1",
        "status": "VERIFIED",
    }
    entry["content_hash"] = schedule_hash(entry)
    return CalendarService(
        db_session,
        weather_service=weather,
        stage_registry=CropStageRegistry([entry]),
    )


async def test_generate_creates_full_schedule(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)

    events = await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))
    assert len(events) == 15  # default schedule length
    row, _ = events[0]
    assert row.season is not None
    assert all(r.status == EventStatus.PENDING.value for r, _ in events)
    assert all(r.registry_verification_status == "VERIFIED" for r, _ in events)
    assert all(r.registry_source_reference == "TEST-ONLY" for r, _ in events)


async def test_generate_requires_sowing_date(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user, sowing_date=None)
    # Farm defaults sowing_date to today; clear it to hit the guard.
    farm.sowing_date = None
    await db_session.flush()
    service = _service(db_session)
    with pytest.raises(SowingDateRequiredError):
        await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))


async def test_generate_rejects_foreign_farm(db_session):
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    farm = await _make_farm(db_session, owner)
    service = _service(db_session)
    with pytest.raises(FarmNotFoundError):
        await service.generate(other, GenerateCalendarRequest(farm_id=farm.id))
    with pytest.raises(FarmNotFoundError):
        await service.generate(owner, GenerateCalendarRequest(farm_id=uuid.uuid4()))


async def test_generate_rejects_context_overrides_that_do_not_match_farm(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user, crop="wheat", sowing_date=date(2026, 8, 1))
    service = _service(db_session)

    with pytest.raises(FarmCalendarContextMismatchError):
        await service.generate(
            user, GenerateCalendarRequest(farm_id=farm.id, crop="paddy")
        )
    with pytest.raises(FarmCalendarContextMismatchError):
        await service.generate(
            user,
            GenerateCalendarRequest(farm_id=farm.id, sowing_date=date(2026, 8, 2)),
        )


async def test_regenerate_replaces_pending_but_keeps_completed(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)

    first = await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))
    # Complete one activity, then regenerate.
    done_id = first[0][0].id
    await service.update_event(
        user, done_id, UpdateCalendarEventRequest(status=EventStatus.DONE.value)
    )
    await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))

    timeline = await service.timeline(user, farm_id=farm.id)
    done = [r for r, _ in timeline if r.status == EventStatus.DONE.value]
    pending = [r for r, _ in timeline if r.status == EventStatus.PENDING.value]
    assert len(done) == 1  # completed history preserved
    assert len(pending) == 15  # a fresh pending plan


async def test_registry_version_change_hides_old_schedule(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))

    service.stage_registry = CropStageRegistry([])
    assert await service.timeline(user, farm_id=farm.id) == []


async def test_notifications_ignore_calendar_from_non_active_pack(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))

    source = NotificationSources(db_session, now=datetime.now(UTC), enable_weather=False)
    assert await source._collect_calendar(user) == []


async def test_today_upcoming_completed_missed(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)  # sowing = today
    service = _service(db_session)
    await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))

    today = await service.today(user, farm_id=farm.id)
    assert any(r.code == "sowing" for r, _ in today)

    upcoming = await service.upcoming(user, farm_id=farm.id, days=7)
    assert all(r.scheduled_date >= _today() for r, _ in upcoming)
    assert any(r.code == "irrigation_1" for r, _ in upcoming)

    missed = await service.missed(user, farm_id=farm.id)
    codes = {r.code for r, _ in missed}
    assert "land_prep" in codes  # scheduled 12 days before sowing/today

    completed = await service.completed(user, farm_id=farm.id)
    assert completed == []


async def test_update_marks_done_with_timestamp(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    events = await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))
    target = events[0][0]

    row, _ = await service.update_event(
        user, target.id, UpdateCalendarEventRequest(status=EventStatus.DONE.value)
    )
    assert row.status == EventStatus.DONE.value
    assert row.completed_at is not None

    with pytest.raises(CalendarEventNotFoundError):
        await service.update_event(user, uuid.uuid4(), UpdateCalendarEventRequest(status="done"))


async def test_summary_counts(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    events = await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))
    await service.update_event(user, events[0][0].id, UpdateCalendarEventRequest(status="done"))

    summary = await service.summary(user, farm.id)
    assert summary.total == 15
    assert summary.completed == 1
    assert summary.missed >= 1
    assert summary.season is not None


async def test_weather_advisory_delays_irrigation_on_heavy_rain(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)  # sowing today, drip
    service = _service(db_session, raw=_heavy_rain_raw())
    await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))

    upcoming = await service.upcoming(user, farm_id=farm.id, days=7)
    irrigation = [
        (r, adv)
        for r, adv in upcoming
        if r.weather_dependency == WeatherDependency.IRRIGATION.value
    ]
    assert irrigation
    assert any(adv == WeatherAdvisory.DELAY_IRRIGATION.value for _, adv in irrigation)


async def test_weather_advisory_absent_without_weather_service(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    service.weather_service = None
    await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))

    upcoming = await service.upcoming(user, farm_id=farm.id, days=7)
    assert all(adv == WeatherAdvisory.NONE.value for _, adv in upcoming)


async def test_ownership_isolation_on_reads(db_session):
    owner = await _make_user(db_session, uid="fb-owner2")
    other = await _make_user(db_session, uid="fb-other2")
    farm = await _make_farm(db_session, owner)
    service = _service(db_session)
    await service.generate(owner, GenerateCalendarRequest(farm_id=farm.id))

    with pytest.raises(FarmNotFoundError):
        await service.for_farm(other, farm.id)
    # A different user sees an empty unfiltered timeline.
    assert await service.timeline(other) == []


async def test_rainfed_farm_marks_irrigation_low_priority(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user, irrigation_type="rainfed")
    service = _service(db_session)
    events = await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))

    irrigation = [
        r for r, _ in events if r.weather_dependency == WeatherDependency.IRRIGATION.value
    ]
    assert irrigation
    assert all(r.priority == "low" for r in irrigation)
    assert all(r.reminder_enabled is False for r in irrigation)


async def test_missed_excludes_completed(db_session):
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session)
    events = await service.generate(user, GenerateCalendarRequest(farm_id=farm.id))

    land_prep = next(r for r, _ in events if r.code == "land_prep")
    assert land_prep.scheduled_date < _today()
    await service.update_event(user, land_prep.id, UpdateCalendarEventRequest(status="done"))
    missed = await service.missed(user, farm_id=farm.id)
    assert all(r.code != "land_prep" for r, _ in missed)
