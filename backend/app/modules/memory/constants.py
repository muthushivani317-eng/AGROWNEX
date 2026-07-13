"""Farm Memory Engine constants (docs: AI Memory; never fabricate history).

Transparent, tunable enums and thresholds so every memory's importance, season and
observed/inferred classification is fully reproducible. Missing modules simply emit
no memory — they are never replaced with invented history (docs/PRODUCT_RULES.md).
"""
from __future__ import annotations

import os
from enum import StrEnum

DEFAULT_LANGUAGE = "ta"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Provider selection (future: embeddings / vector search / RAG / LLM synthesis).
MEMORY_PROVIDER = os.getenv("MEMORY_PROVIDER", "")


class SourceModule(StrEnum):
    """Every module the memory engine can learn from."""

    DISEASE = "disease"
    GROWTH = "growth"
    WEATHER = "weather"
    SATELLITE = "satellite"
    SOIL = "soil"
    NUTRIENT = "nutrient"
    SCHEMES = "schemes"
    MARKET = "market"
    EXPERTS = "experts"
    AI_CHAT = "ai_chat"
    PRODUCE = "produce"
    CALENDAR = "calendar"
    IOT = "iot"  # future — reserved, no collector in V1


class EventType(StrEnum):
    """Stable structured event codes emitted by the collectors."""

    DISEASE_DIAGNOSED = "disease_diagnosed"
    DISEASE_RESOLVED = "disease_resolved"
    NUTRIENT_DEFICIENCY_DETECTED = "nutrient_deficiency_detected"
    SOIL_REPORT_UPLOADED = "soil_report_uploaded"
    SATELLITE_VEGETATION_DECLINE = "satellite_vegetation_decline"
    SATELLITE_SCAN = "satellite_scan"
    GROWTH_TRACKED = "growth_tracked"
    GROWTH_DECLINE = "growth_decline"
    WEATHER_EVENT = "weather_event"
    CALENDAR_COMPLETED = "crop_calendar_completed"
    HARVEST_SUBMITTED = "harvest_submitted"
    EXPERT_CONSULTATION_RESOLVED = "expert_consultation_resolved"
    EXPERT_CONSULTATION_OPENED = "expert_consultation_opened"
    GOVERNMENT_SCHEME_SAVED = "government_scheme_saved"
    MARKET_PRICE_VIEWED = "market_price_viewed"
    AI_CONVERSATION = "ai_conversation"


class Importance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


IMPORTANCE_SCORE: dict[str, int] = {
    Importance.LOW.value: 25,
    Importance.MEDIUM.value: 50,
    Importance.HIGH.value: 75,
    Importance.CRITICAL.value: 95,
}
IMPORTANCE_ORDER: dict[str, int] = {
    Importance.LOW.value: 0,
    Importance.MEDIUM.value: 1,
    Importance.HIGH.value: 2,
    Importance.CRITICAL.value: 3,
}


class Season(StrEnum):
    """Tamil Nadu cropping seasons, derived transparently from the calendar month."""

    KHARIF = "kharif"    # Kar / Kuruvai — sowing Jun–Oct
    RABI = "rabi"        # Samba / Thaladi — Oct–Feb
    SUMMER = "summer"    # Mar–May
    UNKNOWN = "unknown"


class SummaryPeriod(StrEnum):
    SEASON = "season"
    YEAR = "year"


class LinkType(StrEnum):
    """How two memories relate (transparent, deterministic)."""

    FOLLOWS = "follows"        # the previous memory from the same module
    RELATES = "relates"        # cross-module, same crop + season
    RESOLVES = "resolves"      # a resolution of an earlier issue


class ObservationKind(StrEnum):
    OBSERVED = "observed"      # directly recorded (photo, report, farmer action)
    INFERRED = "inferred"      # derived (remote sensing, forecast, model)


# --------------------------------------------------------------------------- #
# Season derivation (docs: transparent + reproducible).
# --------------------------------------------------------------------------- #
def season_for_month(month: int) -> str:
    """Map a 1-12 month to a Tamil-Nadu cropping season (pure, reproducible)."""
    if month in (6, 7, 8, 9, 10):
        return Season.KHARIF.value
    if month in (11, 12, 1, 2):
        return Season.RABI.value
    if month in (3, 4, 5):
        return Season.SUMMER.value
    return Season.UNKNOWN.value


def season_year(year: int, month: int) -> int:
    """The agricultural year a month belongs to.

    Rabi spans a calendar boundary (Oct–Feb); Jan/Feb belong to the *previous*
    year's Rabi season so a season's memories group together.
    """
    if month in (1, 2):
        return year - 1
    return year


# Distinct events that are "duplicates" within the same day collapse into one memory
# (docs: merge duplicate events). The dedup key makes rebuild idempotent + immutable.
DEDUP_DATE_FMT = "%Y-%m-%d"
