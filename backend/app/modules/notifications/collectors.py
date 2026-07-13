"""Deterministic event collectors (docs: RULE ENGINE — no AI required).

One pure function per event source. Each takes a *lightweight view* of that
module's data (built by the service from the module's own repository — the source
modules are never modified) and returns ``CandidateEvent``s. All rules are
transparent thresholds from ``constants`` so results are reproducible and unit
-testable without a database. The engine then resolves each candidate against the
rule table; the service persists and delivers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.modules.notifications.constants import (
    AI_CONVERSATION_REMINDER_DAYS,
    AI_FOLLOW_UP_DAYS,
    DISEASE_HIGH_CONFIDENCE,
    GROWTH_HEALTH_DELTA,
    GROWTH_STALE_DAYS,
    HARVEST_APPROACHING_WINDOW_DAYS,
    MARKET_PRICE_MOVE_PERCENT,
    OFFER_EXPIRING_WINDOW_DAYS,
    SCHEME_CLOSING_WINDOW_DAYS,
    WEATHER_CODE_EVENTS,
    WEATHER_LOW_TEMP_C,
    NotificationModule,
)
from app.modules.notifications.engine import CandidateEvent

_M = NotificationModule


def _key(module: str, event_type: str, *parts: object) -> str:
    """A stable, human-readable dedup key: ``module:event:part1:part2``."""
    return ":".join([module, event_type, *[str(p) for p in parts]])


# --------------------------------------------------------------------------- #
# Weather — reuses the Weather module's insight codes (never duplicated)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class WeatherSnapshot:
    farm_id: str
    insight_codes: list[str]
    daily_min_temp_c: float | None = None


def collect_weather(snapshot: WeatherSnapshot, *, day: date) -> list[CandidateEvent]:
    events: dict[str, CandidateEvent] = {}
    for code in snapshot.insight_codes:
        event_type = WEATHER_CODE_EVENTS.get(code)
        if event_type is None or event_type in events:
            continue
        events[event_type] = CandidateEvent(
            module=_M.WEATHER.value,
            event_type=event_type,
            dedup_key=_key(_M.WEATHER.value, event_type, snapshot.farm_id, day),
            payload={"code": code, "farm_id": snapshot.farm_id},
            farm_id=snapshot.farm_id,
        )
    if (
        snapshot.daily_min_temp_c is not None
        and snapshot.daily_min_temp_c <= WEATHER_LOW_TEMP_C
        and "low_temperature" not in events
    ):
        events["low_temperature"] = CandidateEvent(
            module=_M.WEATHER.value,
            event_type="low_temperature",
            dedup_key=_key(_M.WEATHER.value, "low_temperature", snapshot.farm_id, day),
            payload={"temp": round(snapshot.daily_min_temp_c), "farm_id": snapshot.farm_id},
            farm_id=snapshot.farm_id,
        )
    return list(events.values())


# --------------------------------------------------------------------------- #
# Crop Calendar — one aggregate per bucket per farm per day
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CalendarCounts:
    farm_id: str
    today: int = 0
    upcoming: int = 0
    missed: int = 0


def collect_calendar(counts: CalendarCounts, *, day: date) -> list[CandidateEvent]:
    events: list[CandidateEvent] = []
    for event_type, count in (
        ("today_task", counts.today),
        ("upcoming_task", counts.upcoming),
        ("missed_activity", counts.missed),
    ):
        if count <= 0:
            continue
        events.append(
            CandidateEvent(
                module=_M.CALENDAR.value,
                event_type=event_type,
                dedup_key=_key(_M.CALENDAR.value, event_type, counts.farm_id, day),
                payload={"count": count, "farm_id": counts.farm_id},
                farm_id=counts.farm_id,
            )
        )
    return events


# --------------------------------------------------------------------------- #
# Disease — per analysed report (permanent dedup by report id)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DiseaseReportView:
    report_id: str
    farm_id: str | None
    crop: str | None
    disease: str | None
    confidence: int | None
    needs_expert_review: bool
    quality_poor: bool = False


def collect_disease(report: DiseaseReportView) -> list[CandidateEvent]:
    events: list[CandidateEvent] = []
    if report.quality_poor:
        events.append(
            CandidateEvent(
                module=_M.DISEASE.value,
                event_type="poor_image_quality",
                dedup_key=_key(_M.DISEASE.value, "poor_image_quality", report.report_id),
                payload={"report_id": report.report_id},
                farm_id=report.farm_id,
            )
        )
        return events
    if (
        report.disease
        and report.confidence is not None
        and report.confidence >= DISEASE_HIGH_CONFIDENCE
    ):
        events.append(
            CandidateEvent(
                module=_M.DISEASE.value,
                event_type="high_confidence_disease",
                dedup_key=_key(
                    _M.DISEASE.value, "high_confidence_disease", report.report_id
                ),
                payload={
                    "report_id": report.report_id,
                    "disease": report.disease,
                    "crop": report.crop,
                    "confidence": report.confidence,
                },
                farm_id=report.farm_id,
            )
        )
    if report.needs_expert_review:
        events.append(
            CandidateEvent(
                module=_M.DISEASE.value,
                event_type="expert_review_needed",
                dedup_key=_key(
                    _M.DISEASE.value, "expert_review_needed", report.report_id
                ),
                payload={"report_id": report.report_id, "crop": report.crop},
                farm_id=report.farm_id,
            )
        )
    return events


# --------------------------------------------------------------------------- #
# Crop Growth Monitor
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GrowthView:
    session_id: str
    farm_id: str | None
    week_number: int
    last_image_days_ago: int | None
    latest_health_delta: int | None = None
    latest_timeline_id: str | None = None


def collect_growth(view: GrowthView) -> list[CandidateEvent]:
    events: list[CandidateEvent] = []
    if view.last_image_days_ago is not None and view.last_image_days_ago >= GROWTH_STALE_DAYS:
        next_week = view.week_number + 1
        events.append(
            CandidateEvent(
                module=_M.GROWTH.value,
                event_type="weekly_reminder",
                dedup_key=_key(
                    _M.GROWTH.value, "weekly_reminder", view.session_id, next_week
                ),
                payload={"session_id": view.session_id, "week": next_week},
                farm_id=view.farm_id,
            )
        )
    if view.latest_health_delta is not None and view.latest_timeline_id is not None:
        if view.latest_health_delta <= -GROWTH_HEALTH_DELTA:
            events.append(
                CandidateEvent(
                    module=_M.GROWTH.value,
                    event_type="growth_decline",
                    dedup_key=_key(
                        _M.GROWTH.value, "growth_decline", view.latest_timeline_id
                    ),
                    payload={
                        "session_id": view.session_id,
                        "delta": view.latest_health_delta,
                    },
                    farm_id=view.farm_id,
                )
            )
        elif view.latest_health_delta >= GROWTH_HEALTH_DELTA:
            events.append(
                CandidateEvent(
                    module=_M.GROWTH.value,
                    event_type="growth_improvement",
                    dedup_key=_key(
                        _M.GROWTH.value, "growth_improvement", view.latest_timeline_id
                    ),
                    payload={
                        "session_id": view.session_id,
                        "delta": view.latest_health_delta,
                    },
                    farm_id=view.farm_id,
                )
            )
    return events


# --------------------------------------------------------------------------- #
# Market — per favourite crop (reuses verified prices; never fabricated)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MarketMoveView:
    favourite_id: str
    crop: str
    market: str | None
    latest_price: float
    # None → brand-new price for a favourite (no history) → favourite_crop_alert.
    change_percent: float | None = None


def collect_market(view: MarketMoveView, *, day: date) -> list[CandidateEvent]:
    if view.change_percent is None:
        return [
            CandidateEvent(
                module=_M.MARKET.value,
                event_type="favourite_crop_alert",
                dedup_key=_key(
                    _M.MARKET.value, "favourite_crop_alert", view.favourite_id, day
                ),
                payload={
                    "crop": view.crop,
                    "market": view.market,
                    "price": view.latest_price,
                },
                farm_id=None,
            )
        ]
    if abs(view.change_percent) < MARKET_PRICE_MOVE_PERCENT:
        return []
    event_type = "price_increase" if view.change_percent > 0 else "price_decrease"
    return [
        CandidateEvent(
            module=_M.MARKET.value,
            event_type=event_type,
            dedup_key=_key(_M.MARKET.value, event_type, view.favourite_id, day),
            payload={
                "crop": view.crop,
                "market": view.market,
                "price": view.latest_price,
                "change": round(view.change_percent, 1),
            },
            farm_id=None,
        )
    ]


# --------------------------------------------------------------------------- #
# Government Schemes — eligible now; a closing reminder may be scheduled
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SchemeView:
    scheme_id: str
    title: str
    days_to_deadline: int | None = None
    is_newly_created: bool = False


def collect_schemes(view: SchemeView, *, now: datetime) -> list[CandidateEvent]:
    events: list[CandidateEvent] = [
        CandidateEvent(
            module=_M.SCHEMES.value,
            event_type="scheme_eligible",
            dedup_key=_key(_M.SCHEMES.value, "scheme_eligible", view.scheme_id),
            payload={"scheme_id": view.scheme_id, "title": view.title},
        )
    ]
    if view.is_newly_created:
        events.append(
            CandidateEvent(
                module=_M.SCHEMES.value,
                event_type="new_scheme",
                dedup_key=_key(_M.SCHEMES.value, "new_scheme", view.scheme_id),
                payload={"scheme_id": view.scheme_id, "title": view.title},
            )
        )
    if view.days_to_deadline is not None and view.days_to_deadline >= 0:
        # Within the window → notify now; further out → schedule for the queue.
        scheduled_for = (
            None
            if view.days_to_deadline <= SCHEME_CLOSING_WINDOW_DAYS
            else now + timedelta(days=view.days_to_deadline - SCHEME_CLOSING_WINDOW_DAYS)
        )
        events.append(
            CandidateEvent(
                module=_M.SCHEMES.value,
                event_type="application_closing",
                dedup_key=_key(
                    _M.SCHEMES.value, "application_closing", view.scheme_id
                ),
                payload={
                    "scheme_id": view.scheme_id,
                    "title": view.title,
                    "days_left": view.days_to_deadline,
                },
                scheduled_for=scheduled_for,
            )
        )
    return events


# --------------------------------------------------------------------------- #
# Sell My Produce — per upcoming offer (buyer_interest is future — never faked)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ProduceOfferView:
    offer_id: str
    farm_id: str | None
    crop: str
    days_to_harvest: int


def collect_produce(view: ProduceOfferView) -> list[CandidateEvent]:
    if 0 <= view.days_to_harvest <= HARVEST_APPROACHING_WINDOW_DAYS:
        return [
            CandidateEvent(
                module=_M.PRODUCE.value,
                event_type="harvest_approaching",
                dedup_key=_key(_M.PRODUCE.value, "harvest_approaching", view.offer_id),
                payload={
                    "offer_id": view.offer_id,
                    "crop": view.crop,
                    "days_left": view.days_to_harvest,
                },
                farm_id=view.farm_id,
            )
        ]
    if -OFFER_EXPIRING_WINDOW_DAYS <= view.days_to_harvest < 0:
        return [
            CandidateEvent(
                module=_M.PRODUCE.value,
                event_type="offer_expiring",
                dedup_key=_key(_M.PRODUCE.value, "offer_expiring", view.offer_id),
                payload={"offer_id": view.offer_id, "crop": view.crop},
                farm_id=view.farm_id,
            )
        ]
    return []


# --------------------------------------------------------------------------- #
# AI — gentle re-engagement (silence-based; deterministic)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AIActivityView:
    conversation_id: str | None
    days_since_last: int | None


def collect_ai(view: AIActivityView, *, day: date) -> list[CandidateEvent]:
    if view.conversation_id is None or view.days_since_last is None:
        return []
    if view.days_since_last >= AI_CONVERSATION_REMINDER_DAYS:
        event_type = "conversation_reminder"
    elif view.days_since_last >= AI_FOLLOW_UP_DAYS:
        event_type = "follow_up_reminder"
    else:
        return []
    return [
        CandidateEvent(
            module=_M.AI.value,
            event_type=event_type,
            dedup_key=_key(_M.AI.value, event_type, view.conversation_id, day),
            payload={
                "conversation_id": view.conversation_id,
                "days": view.days_since_last,
            },
        )
    ]


# --------------------------------------------------------------------------- #
# Expert Connect — consultation lifecycle events (assignment / reply / resolved)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ExpertConsultationView:
    consultation_id: str
    subject: str
    assigned: bool
    expert_name: str | None = None
    latest_expert_message_id: str | None = None
    resolved_by_expert: bool = False


def collect_experts(view: ExpertConsultationView) -> list[CandidateEvent]:
    events: list[CandidateEvent] = []
    if view.assigned:
        events.append(
            CandidateEvent(
                module=_M.EXPERTS.value,
                event_type="consultation_assigned",
                dedup_key=_key(
                    _M.EXPERTS.value, "consultation_assigned", view.consultation_id
                ),
                payload={
                    "consultation_id": view.consultation_id,
                    "subject": view.subject,
                    "expert": view.expert_name,
                },
            )
        )
    # Fires only on a genuine expert reply — never fabricated (none in V1).
    if view.latest_expert_message_id is not None:
        events.append(
            CandidateEvent(
                module=_M.EXPERTS.value,
                event_type="consultation_reply",
                dedup_key=_key(
                    _M.EXPERTS.value, "consultation_reply", view.latest_expert_message_id
                ),
                payload={
                    "consultation_id": view.consultation_id,
                    "subject": view.subject,
                    "expert": view.expert_name,
                },
            )
        )
    if view.resolved_by_expert:
        events.append(
            CandidateEvent(
                module=_M.EXPERTS.value,
                event_type="consultation_resolved",
                dedup_key=_key(
                    _M.EXPERTS.value, "consultation_resolved", view.consultation_id
                ),
                payload={
                    "consultation_id": view.consultation_id,
                    "subject": view.subject,
                },
            )
        )
    return events


# --------------------------------------------------------------------------- #
# Soil Intelligence — a processed report, and a deficiency alert if warranted
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SoilReportView:
    report_id: str
    farm_id: str
    source: str
    has_deficiency: bool = False
    deficiency_count: int = 0


def collect_soil(view: SoilReportView) -> list[CandidateEvent]:
    events = [
        CandidateEvent(
            module=_M.SOIL.value,
            event_type="report_processed",
            dedup_key=_key(_M.SOIL.value, "report_processed", view.report_id),
            payload={"farm_id": view.farm_id, "source": view.source},
            farm_id=view.farm_id,
        )
    ]
    if view.has_deficiency:
        events.append(
            CandidateEvent(
                module=_M.SOIL.value,
                event_type="deficiency_alert",
                dedup_key=_key(_M.SOIL.value, "deficiency_alert", view.report_id),
                payload={"farm_id": view.farm_id, "count": view.deficiency_count},
                farm_id=view.farm_id,
            )
        )
    return events


# --------------------------------------------------------------------------- #
# Satellite Intelligence — vegetation decline / imagery unavailable
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SatelliteSessionView:
    session_id: str
    farm_id: str
    has_vegetation_alert: bool = False
    unavailable: bool = False


def collect_satellite(view: SatelliteSessionView) -> list[CandidateEvent]:
    events: list[CandidateEvent] = []
    if view.has_vegetation_alert:
        events.append(
            CandidateEvent(
                module=_M.SATELLITE.value,
                event_type="vegetation_decline",
                dedup_key=_key(
                    _M.SATELLITE.value, "vegetation_decline", view.session_id
                ),
                payload={"farm_id": view.farm_id},
                farm_id=view.farm_id,
            )
        )
    if view.unavailable:
        events.append(
            CandidateEvent(
                module=_M.SATELLITE.value,
                event_type="imagery_unavailable",
                dedup_key=_key(
                    _M.SATELLITE.value, "imagery_unavailable", view.session_id
                ),
                payload={"farm_id": view.farm_id},
                farm_id=view.farm_id,
            )
        )
    return events


# --------------------------------------------------------------------------- #
# Nutrient Deficiency AI — a confirmed deficiency, or a soil-test recommendation
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class NutrientReportView:
    report_id: str
    farm_id: str
    primary_deficiency: str | None
    # A confirmed deficiency (never fabricated — the engine's strongest verdict).
    confirmed: bool = False
    # An unconfirmed/uncertain finding that warrants a soil / tissue test.
    needs_test: bool = False


def collect_nutrient(view: NutrientReportView) -> list[CandidateEvent]:
    events: list[CandidateEvent] = []
    if view.confirmed and view.primary_deficiency:
        events.append(
            CandidateEvent(
                module=_M.NUTRIENT.value,
                event_type="deficiency_detected",
                dedup_key=_key(
                    _M.NUTRIENT.value, "deficiency_detected", view.report_id
                ),
                payload={
                    "report_id": view.report_id,
                    "farm_id": view.farm_id,
                    "nutrient": view.primary_deficiency,
                },
                farm_id=view.farm_id,
            )
        )
    elif view.needs_test:
        events.append(
            CandidateEvent(
                module=_M.NUTRIENT.value,
                event_type="test_recommended",
                dedup_key=_key(_M.NUTRIENT.value, "test_recommended", view.report_id),
                payload={"report_id": view.report_id, "farm_id": view.farm_id},
                farm_id=view.farm_id,
            )
        )
    return events


# --------------------------------------------------------------------------- #
# Crop Intelligence Engine — a high/critical overall risk surfaces as an alert
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class IntelligenceReportView:
    report_id: str
    farm_id: str
    overall_risk: str
    overall_health_score: int | None = None


def collect_intelligence(view: IntelligenceReportView) -> list[CandidateEvent]:
    if view.overall_risk == "critical":
        event_type = "critical_risk"
    elif view.overall_risk == "high":
        event_type = "high_risk"
    else:
        return []
    return [
        CandidateEvent(
            module=_M.INTELLIGENCE.value,
            event_type=event_type,
            dedup_key=_key(_M.INTELLIGENCE.value, event_type, view.report_id),
            payload={
                "report_id": view.report_id,
                "farm_id": view.farm_id,
                "health": view.overall_health_score,
            },
            farm_id=view.farm_id,
        )
    ]
