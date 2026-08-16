"""Crop Calendar constants (docs: Calendar Generation)."""

from __future__ import annotations

from enum import StrEnum


class ActivityType(StrEnum):
    LAND_PREPARATION = "land_preparation"
    SEED_TREATMENT = "seed_treatment"
    SOWING = "sowing"
    IRRIGATION = "irrigation"
    FERTILIZER = "fertilizer"
    WEED_MANAGEMENT = "weed_management"
    PEST_MONITORING = "pest_monitoring"
    DISEASE_INSPECTION = "disease_inspection"
    FLOWERING_OBSERVATION = "flowering_observation"
    HARVEST_PREPARATION = "harvest_preparation"
    HARVEST = "harvest"
    POST_HARVEST = "post_harvest"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EventStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    SKIPPED = "skipped"


class GrowthStage(StrEnum):
    LAND_PREP = "land_prep"
    SEEDLING = "seedling"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    FRUITING = "fruiting"
    MATURITY = "maturity"
    HARVEST = "harvest"
    POST_HARVEST = "post_harvest"


class Season(StrEnum):
    """Cropping season, derived deterministically from the sowing month."""

    KHARIF = "kharif"  # monsoon (Jun–Sep)
    RABI = "rabi"  # winter (Oct–Jan)
    SUMMER = "summer"  # Feb–May


class WeatherDependency(StrEnum):
    """What weather an activity is sensitive to (reused by the adjuster)."""

    NONE = "none"
    IRRIGATION = "irrigation"
    SPRAYING = "spraying"


class WeatherAdvisory(StrEnum):
    """Read-time advisory derived from the reused weather insights."""

    NONE = "none"
    DELAY_IRRIGATION = "delay_irrigation"
    DELAY_SPRAYING = "delay_spraying"
    RECOMMEND_IRRIGATION = "recommend_irrigation"


DEFAULT_UPCOMING_DAYS = 7
# Reminder metadata only (future FCM); no push is scheduled in V1.
DEFAULT_REMINDER_HOUR = 6

# Irrigation methods that depend on rainfall — irrigation tasks are de-emphasised.
RAINFED_IRRIGATION = frozenset({"rainfed", "rain-fed", "rain fed", "none"})

# Weather advisories are only meaningful for tasks inside the forecast horizon.
WEATHER_ADVISORY_HORIZON_DAYS = 3
