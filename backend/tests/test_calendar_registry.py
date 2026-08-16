from datetime import date, timedelta

import pytest
from app.modules.calendar.generator import generate_verified_events
from app.modules.calendar.registry import CropStageRegistry, schedule_hash


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


def test_registry_reports_active_and_unverified_counts_without_activation() -> None:
    verified = raw_entry()
    unverified = raw_entry(status="UNVERIFIED")
    unverified["canonical_crop_id"] = "cotton"
    unverified["content_hash"] = schedule_hash(unverified)
    registry = CropStageRegistry([verified, unverified])

    assert registry.active_count == 1
    assert registry.unverified_count == 1
    assert registry.resolve("cotton") is None
