from datetime import date, timedelta

import pytest
from app.modules.calendar.generator import generate_verified_events
from app.modules.calendar.registry import (
    ACTIVE_CROP_STAGE_REGISTRY,
    CropStageRegistry,
    ScheduleStatus,
    schedule_hash,
)


def raw_entry(*, status: str = "VERIFIED", review_date: date | None = None) -> dict:
    raw = {
        "schema_version": "1.0",
        "canonical_crop_id": "paddy",
        "aliases": ["rice"],
        "variety_or_duration_group": "documented_group",
        "stages": [
            {
                "code": "establishment",
                "label_key": "calendar.stages.establishment",
                "start_offset": 0,
                "end_offset": 10,
                "activities": [
                    {
                        "code": "verified_observation",
                        "activity_type": "sowing",
                        "label_key": "calendar.verified.observation.title",
                        "description_key": "calendar.verified.observation.description",
                        "day_offset": 2,
                        "notification_offset_days": 1,
                        "notification_eligible": True,
                    }
                ],
            }
        ],
        "geographic_limitations": ["documented_region"],
        "season_limitations": ["documented_season"],
        "source_organization": "Test agricultural authority",
        "document_reference": "TEST-DOC-1",
        "reviewer": "Test reviewer",
        "approval_date": date.today().isoformat(),
        "review_date": (review_date or date.today() + timedelta(days=30)).isoformat(),
        "version": "1.0.0",
        "status": status,
    }
    raw["content_hash"] = schedule_hash(raw)
    return raw


def test_verified_registry_entry_generates_deterministic_localized_event() -> None:
    registry = CropStageRegistry([raw_entry()])
    schedule = registry.resolve("rice")
    assert schedule is not None
    first = generate_verified_events(schedule, date(2026, 8, 1))
    second = generate_verified_events(schedule, date(2026, 8, 1))
    assert first == second
    assert first[0].scheduled_date == date(2026, 8, 3)
    assert first[0].title == "calendar.verified.observation.title"


@pytest.mark.parametrize(
    "status",
    ["UNVERIFIED", "EXPERT_REVIEW_PENDING", "SUSPENDED", "DISABLED", "REJECTED"],
)
def test_non_verified_entries_are_never_active(status: str) -> None:
    assert CropStageRegistry([raw_entry(status=status)]).resolve("paddy") is None


@pytest.mark.parametrize("status", ["VERIFIED", "SOURCED_PUBLIC_REFERENCE"])
def test_both_live_statuses_activate(status: str) -> None:
    """VERIFIED (expert-reviewed) and SOURCED_PUBLIC_REFERENCE (compiled from
    a real cited public source, not personally expert-reviewed -- product
    decision 2026-08-17) both resolve for a farmer; only the frontend label
    differs, not whether the schedule is usable."""
    registry = CropStageRegistry([raw_entry(status=status)])
    schedule = registry.resolve("paddy")
    assert schedule is not None
    assert schedule.status.value == status


def test_sourced_public_reference_also_expires() -> None:
    expired = raw_entry(
        status="SOURCED_PUBLIC_REFERENCE",
        review_date=date.today() - timedelta(days=1),
    )
    assert CropStageRegistry([expired]).resolve("paddy") is None


def test_tampered_malformed_and_expired_entries_fail_closed() -> None:
    tampered = raw_entry()
    tampered["reviewer"] = "changed after hashing"
    malformed = raw_entry()
    del malformed["source_organization"]
    expired = raw_entry(review_date=date.today() - timedelta(days=1))
    registry = CropStageRegistry([tampered, malformed, expired])
    assert registry.resolve("paddy") is None


def test_unknown_crop_has_no_generic_fallback() -> None:
    registry = CropStageRegistry([raw_entry()])
    assert registry.resolve("cotton") is None


def test_production_sugarcane_schedule_resolves_and_generates_activities() -> None:
    """Regression: a sugarcane farm must not fail with STAGE_DATA_UNAVAILABLE."""
    schedule = ACTIVE_CROP_STAGE_REGISTRY.resolve("sugarcane")

    assert schedule is not None
    assert schedule.status is ScheduleStatus.SOURCED_PUBLIC_REFERENCE
    assert ACTIVE_CROP_STAGE_REGISTRY.resolve("karumbu") is schedule

    events = generate_verified_events(schedule, date(2026, 8, 20))

    assert len(events) == 16
    assert events[0].code == "form_ridges_furrows_apply_basal_manure"
    assert events[0].scheduled_date == date(2026, 8, 10)
    assert events[0].title.startswith("calendar.verified.sugarcane.")
    assert events[-1].code == "harvest_cane"


def test_registry_reports_active_and_unverified_counts_without_activation() -> None:
    verified = raw_entry()
    unverified = raw_entry(status="UNVERIFIED")
    unverified["canonical_crop_id"] = "cotton"
    unverified["content_hash"] = schedule_hash(unverified)
    registry = CropStageRegistry([verified, unverified])

    assert registry.active_count == 1
    assert registry.unverified_count == 1
    assert registry.resolve("cotton") is None
