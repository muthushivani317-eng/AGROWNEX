"""Notification constants — the deterministic rule table (docs: RULE ENGINE).

``RULES`` is the single source of truth mapping every ``(module, event_type)`` to
its localization keys, severity, priority, expiry and action route. The engine
evaluates it (no AI) and the repository seeds ``notification_templates`` from it,
so rules stay in one place and are future-editable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum

DEFAULT_LANGUAGE = "ta"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Provider selection — absent means the in-app-only mock (no external channel).
NOTIFICATION_PROVIDER = os.getenv("NOTIFICATION_PROVIDER", "")


class NotificationModule(StrEnum):
    WEATHER = "weather"
    DISEASE = "disease"
    CALENDAR = "calendar"
    GROWTH = "growth"
    MARKET = "market"
    SCHEMES = "schemes"
    PRODUCE = "produce"
    AI = "ai"
    EXPERTS = "experts"
    SOIL = "soil"
    SATELLITE = "satellite"
    NUTRIENT = "nutrient"
    INTELLIGENCE = "intelligence"
    SYSTEM = "system"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DeliveryChannel(StrEnum):
    IN_APP = "in_app"
    PUSH = "push"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    VOICE = "voice"


class DeliveryStatus(StrEnum):
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    SKIPPED = "skipped"


# Severity ordering for the "minimum severity" delivery gate.
SEVERITY_ORDER: dict[str, int] = {
    Severity.INFO.value: 0,
    Severity.WARNING.value: 1,
    Severity.CRITICAL.value: 2,
}


@dataclass(frozen=True)
class NotificationRule:
    module: str
    event_type: str
    title_key: str
    message_key: str
    severity: str
    priority: str
    expires_after_hours: int | None
    action_route: str | None = None  # may contain payload placeholders, e.g. {report_id}


def _rule(
    module: NotificationModule,
    event_type: str,
    *,
    severity: Severity,
    priority: Priority,
    expires_after_hours: int | None,
    action_route: str | None = None,
) -> NotificationRule:
    key = f"notifications.rules.{module.value}.{event_type}"
    return NotificationRule(
        module=module.value,
        event_type=event_type,
        title_key=f"{key}.title",
        message_key=f"{key}.message",
        severity=severity.value,
        priority=priority.value,
        expires_after_hours=expires_after_hours,
        action_route=action_route,
    )


_M = NotificationModule
_S = Severity
_P = Priority

# --------------------------------------------------------------------------- #
# The rule table — every event source listed in the module brief.
# --------------------------------------------------------------------------- #
_WEATHER_ROUTE = "/weather"
_DISEASE_ROUTE = "/disease/{report_id}"
_CALENDAR_ROUTE = "/calendar"
_GROWTH_ROUTE = "/growth"
_MARKET_ROUTE = "/market"
_SCHEME_ROUTE = "/schemes/{scheme_id}"
_PRODUCE_ROUTE = "/produce/{offer_id}"
_AI_ROUTE = "/ai"
_CONSULTATION_ROUTE = "/consultations/{consultation_id}"
_SOIL_ROUTE = "/soil?farmId={farm_id}"
_SATELLITE_ROUTE = "/satellite?farmId={farm_id}"
_NUTRIENT_ROUTE = "/nutrient/report/{report_id}"
_INTELLIGENCE_ROUTE = "/intelligence?farmId={farm_id}"

_RULE_LIST: tuple[NotificationRule, ...] = (
    # Weather
    _rule(
        _M.WEATHER,
        "heavy_rain",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=24,
        action_route=_WEATHER_ROUTE,
    ),
    _rule(
        _M.WEATHER,
        "high_wind",
        severity=_S.WARNING,
        priority=_P.MEDIUM,
        expires_after_hours=24,
        action_route=_WEATHER_ROUTE,
    ),
    _rule(
        _M.WEATHER,
        "extreme_heat",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=24,
        action_route=_WEATHER_ROUTE,
    ),
    _rule(
        _M.WEATHER,
        "low_temperature",
        severity=_S.WARNING,
        priority=_P.MEDIUM,
        expires_after_hours=24,
        action_route=_WEATHER_ROUTE,
    ),
    _rule(
        _M.WEATHER,
        "spraying_good_window",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=6,
        action_route=_WEATHER_ROUTE,
    ),
    # Disease
    _rule(
        _M.DISEASE,
        "high_confidence_disease",
        severity=_S.CRITICAL,
        priority=_P.CRITICAL,
        expires_after_hours=168,
        action_route=_DISEASE_ROUTE,
    ),
    _rule(
        _M.DISEASE,
        "expert_review_needed",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=168,
        action_route=_DISEASE_ROUTE,
    ),
    _rule(
        _M.DISEASE,
        "groundnut_pest_review_completed",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=168,
        action_route="/disease/{observation_id}",
    ),
    _rule(
        _M.DISEASE,
        "poor_image_quality",
        severity=_S.INFO,
        priority=_P.LOW,
        expires_after_hours=48,
        action_route="/disease",
    ),
    _rule(
        _M.DISEASE,
        "district_outbreak",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=168,
        action_route="/disease",
    ),
    _rule(
        _M.DISEASE,
        "disease_risk_conditions",
        severity=_S.WARNING,
        priority=_P.MEDIUM,
        expires_after_hours=24,
        action_route="/disease",
    ),
    # Crop Calendar
    _rule(
        _M.CALENDAR,
        "today_task",
        severity=_S.INFO,
        priority=_P.HIGH,
        expires_after_hours=36,
        action_route=_CALENDAR_ROUTE,
    ),
    _rule(
        _M.CALENDAR,
        "upcoming_task",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=96,
        action_route=_CALENDAR_ROUTE,
    ),
    _rule(
        _M.CALENDAR,
        "missed_activity",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=168,
        action_route=_CALENDAR_ROUTE,
    ),
    # Growth Monitor
    _rule(
        _M.GROWTH,
        "weekly_reminder",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=168,
        action_route=_GROWTH_ROUTE,
    ),
    _rule(
        _M.GROWTH,
        "growth_decline",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=168,
        action_route=_GROWTH_ROUTE,
    ),
    _rule(
        _M.GROWTH,
        "growth_improvement",
        severity=_S.INFO,
        priority=_P.LOW,
        expires_after_hours=168,
        action_route=_GROWTH_ROUTE,
    ),
    # Market
    _rule(
        _M.MARKET,
        "price_increase",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=48,
        action_route=_MARKET_ROUTE,
    ),
    _rule(
        _M.MARKET,
        "price_decrease",
        severity=_S.WARNING,
        priority=_P.MEDIUM,
        expires_after_hours=48,
        action_route=_MARKET_ROUTE,
    ),
    _rule(
        _M.MARKET,
        "favourite_crop_alert",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=48,
        action_route=_MARKET_ROUTE,
    ),
    _rule(
        _M.MARKET,
        "price_peak",
        severity=_S.INFO,
        priority=_P.HIGH,
        expires_after_hours=48,
        action_route=_MARKET_ROUTE,
    ),
    # Government Schemes
    _rule(
        _M.SCHEMES,
        "scheme_eligible",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=336,
        action_route=_SCHEME_ROUTE,
    ),
    _rule(
        _M.SCHEMES,
        "application_closing",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=240,
        action_route=_SCHEME_ROUTE,
    ),
    _rule(
        _M.SCHEMES,
        "new_scheme",
        severity=_S.INFO,
        priority=_P.LOW,
        expires_after_hours=336,
        action_route="/schemes",
    ),
    # Sell My Produce
    _rule(
        _M.PRODUCE,
        "offer_submitted",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=72,
        action_route=_PRODUCE_ROUTE,
    ),
    _rule(
        _M.PRODUCE,
        "harvest_approaching",
        severity=_S.INFO,
        priority=_P.HIGH,
        expires_after_hours=336,
        action_route=_PRODUCE_ROUTE,
    ),
    _rule(
        _M.PRODUCE,
        "buyer_interest",
        severity=_S.INFO,
        priority=_P.HIGH,
        expires_after_hours=336,
        action_route=_PRODUCE_ROUTE,
    ),
    _rule(
        _M.PRODUCE,
        "offer_expiring",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=168,
        action_route=_PRODUCE_ROUTE,
    ),
    # AI
    _rule(
        _M.AI,
        "follow_up_reminder",
        severity=_S.INFO,
        priority=_P.LOW,
        expires_after_hours=168,
        action_route=_AI_ROUTE,
    ),
    _rule(
        _M.AI,
        "conversation_reminder",
        severity=_S.INFO,
        priority=_P.LOW,
        expires_after_hours=168,
        action_route=_AI_ROUTE,
    ),
    # Expert Connect
    _rule(
        _M.EXPERTS,
        "consultation_assigned",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=336,
        action_route=_CONSULTATION_ROUTE,
    ),
    _rule(
        _M.EXPERTS,
        "consultation_reply",
        severity=_S.INFO,
        priority=_P.HIGH,
        expires_after_hours=336,
        action_route=_CONSULTATION_ROUTE,
    ),
    _rule(
        _M.EXPERTS,
        "consultation_resolved",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=336,
        action_route=_CONSULTATION_ROUTE,
    ),
    # Soil Intelligence
    _rule(
        _M.SOIL,
        "report_processed",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=336,
        action_route=_SOIL_ROUTE,
    ),
    _rule(
        _M.SOIL,
        "deficiency_alert",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=336,
        action_route=_SOIL_ROUTE,
    ),
    # Satellite Intelligence
    _rule(
        _M.SATELLITE,
        "vegetation_decline",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=336,
        action_route=_SATELLITE_ROUTE,
    ),
    _rule(
        _M.SATELLITE,
        "imagery_unavailable",
        severity=_S.INFO,
        priority=_P.LOW,
        expires_after_hours=168,
        action_route=_SATELLITE_ROUTE,
    ),
    # Nutrient Deficiency AI
    _rule(
        _M.NUTRIENT,
        "deficiency_detected",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=336,
        action_route=_NUTRIENT_ROUTE,
    ),
    _rule(
        _M.NUTRIENT,
        "test_recommended",
        severity=_S.INFO,
        priority=_P.MEDIUM,
        expires_after_hours=168,
        action_route=_NUTRIENT_ROUTE,
    ),
    # Crop Intelligence Engine
    _rule(
        _M.INTELLIGENCE,
        "critical_risk",
        severity=_S.CRITICAL,
        priority=_P.CRITICAL,
        expires_after_hours=168,
        action_route=_INTELLIGENCE_ROUTE,
    ),
    _rule(
        _M.INTELLIGENCE,
        "high_risk",
        severity=_S.WARNING,
        priority=_P.HIGH,
        expires_after_hours=168,
        action_route=_INTELLIGENCE_ROUTE,
    ),
)

RULES: dict[tuple[str, str], NotificationRule] = {(r.module, r.event_type): r for r in _RULE_LIST}


def get_rule(module: str, event_type: str) -> NotificationRule | None:
    return RULES.get((module, event_type))


# Thresholds shared by the deterministic generators (transparent + tunable).
UPCOMING_TASK_WINDOW_DAYS = 3
SCHEME_CLOSING_WINDOW_DAYS = 7
HARVEST_APPROACHING_WINDOW_DAYS = 7
OFFER_EXPIRING_WINDOW_DAYS = 3
GROWTH_STALE_DAYS = 7
# Growth reminder cadence by stage category. This is a general agronomic
# heuristic (flowering/fruiting are broadly recognized as the most
# stress-sensitive, yield-critical stages across crops) — NOT verified
# per-crop duration data, since no reliable stage-duration dataset exists
# for all six supported crops (paddy has a specific calendar; banana,
# cotton, groundnut, chilli, redgram fall back to a generic schedule that
# doesn't fit a perennial crop like banana). Do not present these numbers
# to farmers as crop-specific science.
GROWTH_STALE_DAYS_BY_STAGE: dict[str, int] = {
    "germination": 7,
    "seedling": 7,
    "vegetative": 7,
    "flowering": 4,
    "fruiting": 4,
    "maturity": 3,
    "harvest": 3,
    "unknown": 7,
}
GROWTH_HEALTH_DELTA = 5  # health-score change that is worth notifying
DISEASE_HIGH_CONFIDENCE = 90
OUTBREAK_WINDOW_DAYS = 14
OUTBREAK_MIN_DISTINCT_FARMS = 3
MARKET_PRICE_MOVE_PERCENT = 5.0
WEATHER_LOW_TEMP_C = 15.0  # daily min at/below this → low-temperature alert
NEW_SCHEME_RECENT_DAYS = 14  # a scheme created within N days is "new"
AI_FOLLOW_UP_DAYS = 3  # no chat for N days → gentle follow-up reminder
AI_CONVERSATION_REMINDER_DAYS = 14  # long silence → conversation reminder

# Weather insight codes (produced by the Weather module) → notification events.
# Reuses the weather engine's output — weather logic is never duplicated here.
WEATHER_CODE_EVENTS: dict[str, str] = {
    "heavy_rain.severe": "heavy_rain",
    "heavy_rain.expected": "heavy_rain",
    "wind.strong": "high_wind",
    "heat_stress.extreme": "extreme_heat",
    "heat_stress.high": "extreme_heat",
    "spraying.good_window": "spraying_good_window",
}

# Default per-module preference flags (all on — farmers opt out, never in).
MODULE_PREFERENCE_FIELDS: dict[str, str] = {
    NotificationModule.WEATHER.value: "weather_enabled",
    NotificationModule.DISEASE.value: "disease_enabled",
    NotificationModule.CALENDAR.value: "calendar_enabled",
    NotificationModule.GROWTH.value: "growth_enabled",
    NotificationModule.MARKET.value: "market_enabled",
    NotificationModule.SCHEMES.value: "scheme_enabled",
    NotificationModule.PRODUCE.value: "produce_enabled",
    NotificationModule.AI.value: "ai_enabled",
    NotificationModule.SYSTEM.value: "system_enabled",
}

# Channels attempted for a stored notification, in order. In-app is always on;
# the rest are future external channels behind the provider seam (off until wired).
DEFAULT_DELIVERY_CHANNELS: tuple[str, ...] = (DeliveryChannel.IN_APP.value,)


def severity_at_least(severity: str, minimum: str) -> bool:
    """True when ``severity`` meets or exceeds the ``minimum`` gate (pure)."""
    return SEVERITY_ORDER.get(severity, 0) >= SEVERITY_ORDER.get(minimum, 0)
