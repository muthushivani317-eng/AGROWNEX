"""Enums, thresholds, and feature flags for the unified Daily Task advisory layer.

Feature flags live on `app.core.config.settings` (plain env-backed booleans),
matching the existing pattern for `openai_disease_comparison_enabled` /
`openai_vision_diagnosis_enabled` in `app/core/config.py` -- this app has no
separate flag service, so a new one is not introduced here.

All numeric thresholds are PILOT PLACEHOLDERS, not scientific constants --
kept in one importable module so a threshold review touches one file.
"""
from __future__ import annotations

from enum import StrEnum


class SignalType(StrEnum):
    IRRIGATION_DRYNESS = "irrigation_dryness"
    UNEVEN_GROWTH_ZONE = "uneven_growth_zone"
    DRAINAGE_RISK = "drainage_risk"
    SOWING_GERMINATION_DELAY = "sowing_germination_delay"
    DAMAGE_EVENT = "damage_event"  # drives an Evidence Pack, not a daily task card


class SourceModule(StrEnum):
    SATELLITE = "satellite"
    WEATHER = "weather"
    CALENDAR = "calendar"
    SOIL = "soil"
    NUTRIENT = "nutrient"
    DISEASE = "disease"
    FARMER_REPORTED = "farmer_reported"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Severity(StrEnum):
    INFO = "info"
    ATTENTION = "attention"
    URGENT = "urgent"


class Urgency(StrEnum):
    TODAY = "today"
    WITHIN_48H = "within_48h"
    BEFORE_RAIN = "before_rain"
    THIS_WEEK = "this_week"


class SignalStatus(StrEnum):
    CANDIDATE = "candidate"
    RANKED_SHOWN = "ranked_shown"
    SUPPRESSED_COOLDOWN = "suppressed_cooldown"
    SUPPRESSED_DEDUP = "suppressed_dedup"
    SUPPRESSED_LOW_CONFIDENCE = "suppressed_low_confidence"
    SUPPRESSED_CAP = "suppressed_cap"
    SUPPRESSED_FEATURE_FLAG = "suppressed_feature_flag"
    SUPPRESSED_POLICY = "suppressed_policy"
    EXPIRED_STALE = "expired_stale"


class TaskType(StrEnum):
    IRRIGATION_INSPECTION = "irrigation_inspection"
    UNEVEN_GROWTH_INSPECTION = "uneven_growth_inspection"
    DRAINAGE_INSPECTION = "drainage_inspection"
    SOWING_GERMINATION_CHECK = "sowing_germination_check"
    EVIDENCE_PACK_TRIGGER = "evidence_pack_trigger"


SIGNAL_TO_TASK_TYPE: dict[SignalType, TaskType] = {
    SignalType.IRRIGATION_DRYNESS: TaskType.IRRIGATION_INSPECTION,
    SignalType.UNEVEN_GROWTH_ZONE: TaskType.UNEVEN_GROWTH_INSPECTION,
    SignalType.DRAINAGE_RISK: TaskType.DRAINAGE_INSPECTION,
    SignalType.SOWING_GERMINATION_DELAY: TaskType.SOWING_GERMINATION_CHECK,
    SignalType.DAMAGE_EVENT: TaskType.EVIDENCE_PACK_TRIGGER,
}

# Tier 1 always outranks any other tier in a same-day conflict. Drainage is
# genuinely urgent; the rest of the MVP set is Tier 2/3.
TASK_TIER: dict[TaskType, int] = {
    TaskType.DRAINAGE_INSPECTION: 1,
    TaskType.IRRIGATION_INSPECTION: 2,
    TaskType.SOWING_GERMINATION_CHECK: 2,
    TaskType.UNEVEN_GROWTH_INSPECTION: 3,
    TaskType.EVIDENCE_PACK_TRIGGER: 0,  # not part of the 2-per-day cap at all
}


class TaskStatus(StrEnum):
    ACTIVE = "active"
    RESPONDED = "responded"
    SNOOZED = "snoozed"
    EXPIRED = "expired"
    SUPPRESSED = "suppressed"


class ResponseType(StrEnum):
    DONE = "done"
    PROBLEM_FOUND = "problem_found"
    NO_ISSUE = "no_issue"
    NEED_HELP = "need_help"
    NOT_RELEVANT = "not_relevant"


class EvidencePackConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LIMITED = "limited"


class EvidencePackStatus(StrEnum):
    PENDING_POST_EVENT_DATA = "pending_post_event_data"
    READY = "ready"
    SHARED = "shared"


# --------------------------------------------------------------------------- #
# Ranking / threshold constants (pilot placeholders -- see the Claude Project
# doc "agrowai-daily-task-unified-implementation" Section 5 for provenance).
# --------------------------------------------------------------------------- #
MAX_TASKS_PER_FARMER_PER_DAY = 2
TASK_COOLDOWN_DAYS_DEFAULT = 6
TASK_COOLDOWN_DAYS_NO_ISSUE = 6
TASK_COOLDOWN_DAYS_NOT_RELEVANT = 21
ZONE_MIN_CONSECUTIVE_SCANS = 2
ZONE_MIN_AREA_FRACTION = 0.10
IRRIGATION_NDMI_RELATIVE_DROP = 0.15
IRRIGATION_SUPPRESS_IF_RAIN_WITHIN_MM = 10.0
IRRIGATION_SUPPRESS_IF_RAIN_FORECAST_MM = 5.0
DRAINAGE_HEAVY_RAIN_MM_24H = 40.0
SOWING_GRACE_PERIOD_DAYS = 7
SOWING_EXPECTED_EMERGENCE_DAYS_DEFAULT = 15  # used when no calendar emergence event is found for the crop
SIGNAL_VALIDITY_HOURS: dict[SignalType, int] = {
    SignalType.IRRIGATION_DRYNESS: 72,
    SignalType.DRAINAGE_RISK: 36,
    SignalType.SOWING_GERMINATION_DELAY: 96,
    SignalType.UNEVEN_GROWTH_ZONE: 168,
    SignalType.DAMAGE_EVENT: 720,
}


def is_task_type_enabled(task_type: TaskType) -> bool:
    """Reads the real per-task-type flags from `app.core.config.settings`
    (see Settings.daily_task_* below) rather than a second, parallel flag
    dict -- imported lazily to avoid a settings-import cycle at module load.
    """
    from app.core.config import settings

    return {
        TaskType.IRRIGATION_INSPECTION: settings.daily_tasks_enabled,
        TaskType.UNEVEN_GROWTH_INSPECTION: settings.daily_tasks_enabled
        and settings.uneven_growth_enabled,
        TaskType.DRAINAGE_INSPECTION: settings.daily_tasks_enabled
        and settings.cautious_waterlogging_tasks_enabled,
        TaskType.SOWING_GERMINATION_CHECK: settings.daily_tasks_enabled,
        TaskType.EVIDENCE_PACK_TRIGGER: settings.evidence_pack_enabled,
    }.get(task_type, False)
