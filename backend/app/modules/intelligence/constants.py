"""Crop Intelligence constants (docs: aggregate; never fabricate missing data).

Transparent, tunable weights and thresholds so the overall health score, confidence
and risk are fully reproducible. Missing modules reduce confidence — they are never
replaced with invented values.
"""
from __future__ import annotations

import os
from enum import StrEnum

DEFAULT_LANGUAGE = "ta"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Provider selection (future: LLM reasoning / AI Memory augmentation).
INTELLIGENCE_PROVIDER = os.getenv("INTELLIGENCE_PROVIDER", "")


class HealthCategory(StrEnum):
    """The six health-scoring modules that feed the overall score."""

    DISEASE = "disease"
    NUTRIENT = "nutrient"
    SOIL = "soil"
    SATELLITE = "satellite"
    WEATHER = "weather"
    GROWTH = "growth"


class ModuleSource(StrEnum):
    """Every module the engine can read (health + context modules)."""

    DISEASE = "disease"
    NUTRIENT = "nutrient"
    SOIL = "soil"
    SATELLITE = "satellite"
    WEATHER = "weather"
    GROWTH = "growth"
    CALENDAR = "calendar"
    EXPERT = "expert"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IssueSeverity(StrEnum):
    INFO = "info"
    ADVICE = "advice"
    WARNING = "warning"
    CRITICAL = "critical"


# Ordering helpers.
RISK_ORDER: dict[str, int] = {
    RiskLevel.LOW.value: 0,
    RiskLevel.MEDIUM.value: 1,
    RiskLevel.HIGH.value: 2,
    RiskLevel.CRITICAL.value: 3,
}
RISK_BY_ORDER: dict[int, str] = {v: k for k, v in RISK_ORDER.items()}

PRIORITY_ORDER: dict[str, int] = {
    Priority.HIGH.value: 0,
    Priority.MEDIUM.value: 1,
    Priority.LOW.value: 2,
}
SEVERITY_ORDER: dict[str, int] = {
    IssueSeverity.INFO.value: 0,
    IssueSeverity.ADVICE.value: 1,
    IssueSeverity.WARNING.value: 2,
    IssueSeverity.CRITICAL.value: 3,
}

# --------------------------------------------------------------------------- #
# Overall-health weights per module (normalized over the modules present).
# --------------------------------------------------------------------------- #
MODULE_WEIGHTS: dict[str, float] = {
    HealthCategory.DISEASE.value: 0.22,
    HealthCategory.NUTRIENT.value: 0.18,
    HealthCategory.GROWTH.value: 0.20,
    HealthCategory.SOIL.value: 0.15,
    HealthCategory.SATELLITE.value: 0.15,
    HealthCategory.WEATHER.value: 0.10,
}

# Default per-module confidence when a module lacks its own confidence number.
MODULE_BASE_CONFIDENCE: dict[str, int] = {
    HealthCategory.WEATHER.value: 82,
    HealthCategory.GROWTH.value: 70,
    HealthCategory.SOIL.value: 60,
}

# Coverage vs per-module confidence blend for the overall confidence.
COVERAGE_WEIGHT = 0.55
MODULE_CONFIDENCE_WEIGHT = 0.45

# --------------------------------------------------------------------------- #
# Risk thresholds (overall health → base risk level).
# --------------------------------------------------------------------------- #
RISK_LOW_MIN = 80
RISK_MEDIUM_MIN = 65
RISK_HIGH_MIN = 45  # below this → critical

# A "healthy" farm (no issues worth surfacing).
HEALTHY_MIN = 80

# Confidence below which the engine asks the farmer to gather more data.
LOW_CONFIDENCE = 50

# --------------------------------------------------------------------------- #
# Health sub-score penalties (transparent; 0-100 scale).
# --------------------------------------------------------------------------- #
# Disease / nutrient severity → penalty base.
DISEASE_SEVERITY_PENALTY: dict[str, int] = {
    "none": 0,
    "low": 20,
    "moderate": 45,
    "high": 75,
}
NUTRIENT_SEVERITY_PENALTY: dict[str, int] = {
    "none": 0,
    "mild": 20,
    "moderate": 45,
    "severe": 70,
    "unknown": 25,
}
NUTRIENT_NOT_CONFIRMED_PENALTY = 12
NEEDS_EXPERT_CAP = 60  # a report needing expert review caps its sub-score

# Satellite vegetation_health → base sub-score.
VEGETATION_HEALTH_SCORE: dict[str, int] = {
    "bare": 12,
    "very_low": 28,
    "low": 48,
    "moderate": 66,
    "good": 85,
    "very_good": 95,
}

# Growth risk_level → base sub-score (when no numeric health score is stored).
GROWTH_RISK_SCORE: dict[str, int] = {"low": 82, "medium": 62, "high": 42}

# Weather insight code → suitability penalty.
WEATHER_PENALTY: dict[str, int] = {
    "heavy_rain.severe": 18,
    "heavy_rain.expected": 14,
    "wind.strong": 10,
    "heat_stress.extreme": 18,
    "heat_stress.high": 10,
    "cold.frost": 14,
    "cold.low": 8,
}

# Satellite alert codes that indicate vegetation decline (reused, never duplicated).
SATELLITE_VEGETATION_ALERTS = frozenset(
    {
        "satellite.alert.vegetation_decline",
        "satellite.alert.rapid_ndvi_drop",
        "satellite.alert.abnormal_seasonal_change",
        "satellite.alert.low_vigor",
    }
)
