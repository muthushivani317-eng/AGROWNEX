"""Unit tests for the pure notification engine, rule table, collectors and the
mock delivery provider (no database, deterministic)."""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from app.modules.notifications.collectors import (
    AIActivityView,
    CalendarCounts,
    DiseaseReportView,
    GrowthView,
    MarketMoveView,
    ProduceOfferView,
    SchemeView,
    WeatherSnapshot,
    collect_ai,
    collect_calendar,
    collect_disease,
    collect_growth,
    collect_market,
    collect_produce,
    collect_schemes,
    collect_weather,
)
from app.modules.notifications.constants import RULES, Priority, Severity, get_rule
from app.modules.notifications.engine import (
    CandidateEvent,
    build_drafts,
    draft_from_candidate,
)
from app.modules.notifications.provider import (
    DeliveryRequest,
    MockNotificationProvider,
)

NOW = datetime(2026, 7, 11, 6, 0, tzinfo=UTC)
DAY = date(2026, 7, 11)


# --------------------------------------------------------------------------- #
# Rule table + engine
# --------------------------------------------------------------------------- #
def test_every_event_source_has_a_rule() -> None:
    # Every event listed in the module brief maps to a rule.
    expected = {
        ("weather", "heavy_rain"),
        ("weather", "high_wind"),
        ("weather", "extreme_heat"),
        ("weather", "low_temperature"),
        ("weather", "spraying_good_window"),
        ("disease", "high_confidence_disease"),
        ("disease", "expert_review_needed"),
        ("disease", "poor_image_quality"),
        ("calendar", "today_task"),
        ("calendar", "upcoming_task"),
        ("calendar", "missed_activity"),
        ("growth", "weekly_reminder"),
        ("growth", "growth_decline"),
        ("growth", "growth_improvement"),
        ("market", "price_increase"),
        ("market", "price_decrease"),
        ("market", "favourite_crop_alert"),
        ("market", "price_peak"),
        ("schemes", "scheme_eligible"),
        ("schemes", "application_closing"),
        ("schemes", "new_scheme"),
        ("produce", "harvest_approaching"),
        ("produce", "buyer_interest"),
        ("produce", "offer_expiring"),
        ("ai", "follow_up_reminder"),
        ("ai", "conversation_reminder"),
    }
    assert expected <= set(RULES.keys())


def test_draft_resolves_rule_route_and_expiry() -> None:
    candidate = CandidateEvent(
        module="disease",
        event_type="high_confidence_disease",
        dedup_key="disease:high_confidence_disease:r1",
        payload={"report_id": "r1", "disease": "Blight"},
        farm_id="f1",
    )
    draft = draft_from_candidate(candidate, now=NOW)
    assert draft is not None
    assert draft.severity == Severity.CRITICAL.value
    assert draft.priority == Priority.CRITICAL.value
    assert draft.action_route == "/disease/r1"  # placeholder filled from payload
    # 168h expiry from the rule.
    assert draft.expires_at is not None
    assert (draft.expires_at - NOW).days == 7


def test_unknown_event_yields_no_draft() -> None:
    candidate = CandidateEvent(
        module="weather", event_type="meteor_shower", dedup_key="x"
    )
    assert draft_from_candidate(candidate, now=NOW) is None
    assert build_drafts([candidate], now=NOW) == []


def test_missing_route_placeholder_is_left_intact() -> None:
    # No report_id in the payload → route template is returned as-is (never raises).
    candidate = CandidateEvent(
        module="disease", event_type="expert_review_needed", dedup_key="k", payload={}
    )
    draft = draft_from_candidate(candidate, now=NOW)
    assert draft is not None
    assert draft.action_route == "/disease/{report_id}"


def test_get_rule_lookup() -> None:
    assert get_rule("market", "price_increase") is not None
    assert get_rule("market", "nope") is None


# --------------------------------------------------------------------------- #
# Weather collector
# --------------------------------------------------------------------------- #
def test_weather_maps_insight_codes_to_events() -> None:
    snap = WeatherSnapshot(
        farm_id="f1",
        insight_codes=["heavy_rain.severe", "wind.strong", "heat_stress.high"],
        daily_min_temp_c=12.0,
    )
    events = collect_weather(snap, day=DAY)
    types = {e.event_type for e in events}
    assert types == {"heavy_rain", "high_wind", "extreme_heat", "low_temperature"}
    assert all(e.dedup_key.endswith(str(DAY)) for e in events)


def test_weather_maps_good_spraying_window_and_ignores_warm_nights() -> None:
    snap = WeatherSnapshot(
        farm_id="f1", insight_codes=["spraying.good_window"], daily_min_temp_c=22.0
    )
    events = collect_weather(snap, day=DAY)
    assert [event.event_type for event in events] == ["spraying_good_window"]


# --------------------------------------------------------------------------- #
# Calendar collector
# --------------------------------------------------------------------------- #
def test_calendar_emits_only_nonzero_buckets() -> None:
    events = collect_calendar(
        CalendarCounts(farm_id="f1", today=2, upcoming=0, missed=1), day=DAY
    )
    types = {e.event_type for e in events}
    assert types == {"today_task", "missed_activity"}
    today = next(e for e in events if e.event_type == "today_task")
    assert today.payload["count"] == 2


# --------------------------------------------------------------------------- #
# Disease collector
# --------------------------------------------------------------------------- #
def test_disease_high_confidence_and_expert_review() -> None:
    view = DiseaseReportView(
        report_id="r1",
        farm_id="f1",
        crop="Paddy",
        disease="Blast",
        confidence=95,
        needs_expert_review=True,
    )
    types = {e.event_type for e in collect_disease(view)}
    assert types == {"high_confidence_disease", "expert_review_needed"}


def test_disease_low_confidence_no_high_event() -> None:
    view = DiseaseReportView(
        report_id="r1", farm_id=None, crop="Paddy", disease="Blast",
        confidence=40, needs_expert_review=False,
    )
    assert collect_disease(view) == []


def test_disease_poor_quality_short_circuits() -> None:
    view = DiseaseReportView(
        report_id="r1", farm_id=None, crop=None, disease=None,
        confidence=None, needs_expert_review=False, quality_poor=True,
    )
    events = collect_disease(view)
    assert [e.event_type for e in events] == ["poor_image_quality"]


# --------------------------------------------------------------------------- #
# Growth collector
# --------------------------------------------------------------------------- #
def test_growth_weekly_reminder_when_stale() -> None:
    view = GrowthView(
        session_id="s1", farm_id="f1", week_number=3, last_image_days_ago=8
    )
    events = collect_growth(view)
    assert [e.event_type for e in events] == ["weekly_reminder"]
    assert events[0].payload["week"] == 4


def test_growth_weekly_reminder_uses_stage_threshold() -> None:
    flowering = GrowthView(
        "s1", "f1", 3, last_image_days_ago=4, current_growth_stage="flowering"
    )
    vegetative = GrowthView(
        "s2", "f2", 3, last_image_days_ago=4, current_growth_stage="vegetative"
    )
    unknown_stage = GrowthView(
        "s3", "f3", 3, last_image_days_ago=7, current_growth_stage="unexpected"
    )

    assert [e.event_type for e in collect_growth(flowering)] == ["weekly_reminder"]
    assert collect_growth(vegetative) == []
    assert [e.event_type for e in collect_growth(unknown_stage)] == ["weekly_reminder"]


def test_growth_decline_and_improvement() -> None:
    decline = collect_growth(
        GrowthView("s1", "f1", 3, last_image_days_ago=1,
                   latest_health_delta=-8, latest_timeline_id="t1")
    )
    assert [e.event_type for e in decline] == ["growth_decline"]
    improve = collect_growth(
        GrowthView("s1", "f1", 3, last_image_days_ago=1,
                   latest_health_delta=9, latest_timeline_id="t2")
    )
    assert [e.event_type for e in improve] == ["growth_improvement"]


def test_growth_small_delta_ignored() -> None:
    view = GrowthView("s1", "f1", 3, last_image_days_ago=1,
                      latest_health_delta=2, latest_timeline_id="t1")
    assert collect_growth(view) == []


# --------------------------------------------------------------------------- #
# Market collector
# --------------------------------------------------------------------------- #
def test_market_price_increase_and_decrease() -> None:
    up = collect_market(
        MarketMoveView("fav1", "Paddy", "Mandi", latest_price=2100, change_percent=8.0),
        day=DAY,
    )
    assert [e.event_type for e in up] == ["price_increase"]
    down = collect_market(
        MarketMoveView("fav1", "Paddy", "Mandi", latest_price=1800, change_percent=-9.0),
        day=DAY,
    )
    assert [e.event_type for e in down] == ["price_decrease"]


def test_market_small_move_ignored_and_new_price_alert() -> None:
    flat = collect_market(
        MarketMoveView("fav1", "Paddy", "Mandi", latest_price=2000, change_percent=1.0),
        day=DAY,
    )
    assert flat == []
    fresh = collect_market(
        MarketMoveView("fav1", "Paddy", "Mandi", latest_price=2000, change_percent=None),
        day=DAY,
    )
    assert [e.event_type for e in fresh] == ["favourite_crop_alert"]


def test_market_peak_can_cooccur_with_other_alerts() -> None:
    increased = collect_market(
        MarketMoveView(
            "fav1",
            "Paddy",
            "Mandi",
            latest_price=2200,
            change_percent=10.0,
            is_period_high=True,
        ),
        day=DAY,
    )
    assert [e.event_type for e in increased] == ["price_increase", "price_peak"]

    fresh = collect_market(
        MarketMoveView(
            "fav1",
            "Paddy",
            "Mandi",
            latest_price=2000,
            change_percent=None,
            is_period_high=True,
        ),
        day=DAY,
    )
    assert [e.event_type for e in fresh] == ["favourite_crop_alert", "price_peak"]


# --------------------------------------------------------------------------- #
# Schemes collector — including the future-scheduled reminder
# --------------------------------------------------------------------------- #
def test_scheme_eligible_and_immediate_closing() -> None:
    events = collect_schemes(
        SchemeView("sc1", "PM-KISAN", days_to_deadline=3), now=NOW
    )
    types = {e.event_type for e in events}
    assert types == {"scheme_eligible", "application_closing"}
    closing = next(e for e in events if e.event_type == "application_closing")
    assert closing.scheduled_for is None  # within window → immediate


def test_scheme_closing_far_out_is_scheduled_for_the_queue() -> None:
    events = collect_schemes(
        SchemeView("sc1", "PMFBY", days_to_deadline=20), now=NOW
    )
    closing = next(e for e in events if e.event_type == "application_closing")
    assert closing.scheduled_for is not None
    assert closing.scheduled_for > NOW  # parked in the future queue


def test_scheme_new_flag() -> None:
    events = collect_schemes(
        SchemeView("sc1", "New Scheme", is_newly_created=True), now=NOW
    )
    assert "new_scheme" in {e.event_type for e in events}


# --------------------------------------------------------------------------- #
# Produce collector
# --------------------------------------------------------------------------- #
def test_produce_harvest_approaching_and_expiring() -> None:
    soon = collect_produce(ProduceOfferView("o1", "f1", "Paddy", days_to_harvest=3))
    assert [e.event_type for e in soon] == ["harvest_approaching"]
    passed = collect_produce(ProduceOfferView("o1", "f1", "Paddy", days_to_harvest=-2))
    assert [e.event_type for e in passed] == ["offer_expiring"]
    far = collect_produce(ProduceOfferView("o1", "f1", "Paddy", days_to_harvest=40))
    assert far == []


# --------------------------------------------------------------------------- #
# AI collector
# --------------------------------------------------------------------------- #
def test_ai_reminders_by_silence() -> None:
    follow = collect_ai(AIActivityView("c1", days_since_last=5), day=DAY)
    assert [e.event_type for e in follow] == ["follow_up_reminder"]
    conv = collect_ai(AIActivityView("c1", days_since_last=20), day=DAY)
    assert [e.event_type for e in conv] == ["conversation_reminder"]
    recent = collect_ai(AIActivityView("c1", days_since_last=1), day=DAY)
    assert recent == []
    none = collect_ai(AIActivityView(None, None), day=DAY)
    assert none == []


# --------------------------------------------------------------------------- #
# Delivery provider (mock)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_mock_provider_delivers_in_app_and_skips_external() -> None:
    provider = MockNotificationProvider()
    request = DeliveryRequest(
        notification_id="n1",
        user_id="u1",
        module="weather",
        event_type="heavy_rain",
        title_key="t",
        message_key="m",
        severity="warning",
        priority="high",
        payload={},
        action_route="/weather",
    )
    results = await provider.deliver(request, channels=("in_app", "sms"))
    by_channel = {r.channel: r.status for r in results}
    assert by_channel["in_app"] == "delivered"
    assert by_channel["sms"] == "skipped"  # never claims sent for unwired channels
