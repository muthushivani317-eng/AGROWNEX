"""Privacy, threshold, scheduling, and fan-out tests for district outbreaks."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock

from app.modules.auth.models import User
from app.modules.disease.models import DiseaseReport
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.farms.models import Farm, FarmLocation
from app.modules.notifications.collectors import OutbreakView, collect_outbreak
from app.modules.notifications.engine import CandidateEvent
from app.modules.notifications.jobs import evaluate_weather_alerts
from app.modules.notifications.sources import NotificationSources

NOW = datetime(2026, 8, 9, 6, 0, tzinfo=UTC)


async def _farm(db_session, *, suffix: str, district: str = "Thanjavur") -> Farm:
    user = User(firebase_uid=f"outbreak-{suffix}", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name=f"Field {suffix}", crop="paddy")
    db_session.add(farm)
    await db_session.flush()
    db_session.add(FarmLocation(farm_id=farm.id, district=district, source="gps"))
    await db_session.flush()
    return farm


async def _report(
    db_session,
    farm: Farm,
    *,
    suffix: str,
    created_at: datetime = NOW,
) -> None:
    db_session.add(
        DiseaseReport(
            user_id=farm.user_id,
            farm_id=farm.id,
            image_url=f"memory://outbreak/{suffix}.jpg",
            crop="paddy",
            disease="paddy__blast",
            created_at=created_at,
            language="en",
        )
    )
    await db_session.flush()


async def test_repeated_reports_from_one_or_two_farms_never_reach_threshold(db_session):
    first = await _farm(db_session, suffix="repeat-a")
    second = await _farm(db_session, suffix="repeat-b")
    for index in range(6):
        await _report(db_session, first, suffix=f"a-{index}")
        await _report(db_session, second, suffix=f"b-{index}")

    groups = await DiseaseReportRepository(db_session).district_outbreak_groups(
        since=NOW - timedelta(days=14), min_distinct_farms=3
    )

    assert groups == []


async def test_three_distinct_farms_trigger_identity_free_outbreak_event(db_session):
    first_farm = None
    for suffix in ("three-a", "three-b", "three-c"):
        farm = await _farm(db_session, suffix=suffix, district="  THANJAVUR ")
        first_farm = first_farm or farm
        await _report(db_session, farm, suffix=suffix)

    groups = await DiseaseReportRepository(db_session).district_outbreak_groups(
        since=NOW - timedelta(days=14), min_distinct_farms=3
    )

    assert groups == [("thanjavur", "paddy", "paddy__blast", 3)]
    district, crop, disease, _count = groups[0]
    assert first_farm is not None
    user = await db_session.get(User, first_farm.user_id)
    assert user is not None
    events = await NotificationSources(
        db_session,
        now=NOW,
        enable_weather=False,
        outbreak_index={district: [(crop, disease)]},
    )._collect_outbreak(user)
    assert len(events) == 1
    event = events[0]
    assert event.payload == {"crop": "paddy", "disease": "paddy__blast"}
    assert event.farm_id is None
    assert not ({"farm_id", "user_id"} & event.payload.keys())


class _EmptySources:
    async def collect(self, user: User) -> list[CandidateEvent]:
        del user
        return []


async def test_job_runs_district_aggregate_exactly_once_for_many_users(
    db_session, monkeypatch
):
    for suffix in ("job-a", "job-b", "job-c", "job-d"):
        await _farm(db_session, suffix=suffix)
    aggregate = AsyncMock(return_value=[])
    monkeypatch.setattr(
        DiseaseReportRepository, "district_outbreak_groups", aggregate
    )

    result = await evaluate_weather_alerts(
        db_session, sources=_EmptySources(), now=NOW
    )

    assert result["farmers"] == 4
    aggregate.assert_awaited_once_with(
        since=NOW - timedelta(days=14), min_distinct_farms=3
    )


async def test_report_older_than_window_does_not_reach_threshold(db_session):
    recent_a = await _farm(db_session, suffix="recent-a")
    recent_b = await _farm(db_session, suffix="recent-b")
    old = await _farm(db_session, suffix="old")
    await _report(db_session, recent_a, suffix="recent-a")
    await _report(db_session, recent_b, suffix="recent-b")
    await _report(
        db_session,
        old,
        suffix="old",
        created_at=NOW - timedelta(days=15),
    )

    groups = await DiseaseReportRepository(db_session).district_outbreak_groups(
        since=NOW - timedelta(days=14), min_distinct_farms=3
    )

    assert groups == []


def test_outbreak_dedup_key_is_stable_within_week_and_changes_next_week():
    view = OutbreakView(
        district="thanjavur", crop="paddy", disease="paddy__blast"
    )

    monday = collect_outbreak(view, week=date(2026, 8, 3))[0]
    friday = collect_outbreak(view, week=date(2026, 8, 7))[0]
    next_monday = collect_outbreak(view, week=date(2026, 8, 10))[0]

    assert monday.dedup_key == friday.dedup_key
    assert next_monday.dedup_key != monday.dedup_key
