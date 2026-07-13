"""Soil Intelligence constants (docs/PRODUCT_RULES.md → never fabricate soil data).

The Soil Engine classifies farmer-provided (or future lab/government/satellite)
soil values against transparent, standard agronomic thresholds — the Indian
**Soil Health Card** rating bands — and produces *generic* agronomic advice only.
No commercial fertilizer brands are ever recommended. When a value is unavailable
it stays ``None`` and is reported as "not available" — never invented.
"""
from __future__ import annotations

import os
from enum import StrEnum

DEFAULT_LANGUAGE = "ta"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Provider selection — absent means the mock (no external soil dataset / lab / OCR).
SOIL_PROVIDER = os.getenv("SOIL_PROVIDER", "")


class SoilSource(StrEnum):
    """Where a soil datum came from (drives confidence; never fabricated)."""

    SELF = "self"                       # farmer typed values from a paper card
    SOIL_HEALTH_CARD = "soil_health_card"  # government Soil Health Card
    LAB = "lab"                         # accredited laboratory report
    GOVERNMENT = "government"           # government soil dataset (future)
    SATELLITE = "satellite"            # satellite soil layer (future)
    FARM_REGISTRATION = "farm_registration"  # soil_type the farmer registered
    ESTIMATE = "estimate"              # derived, clearly-flagged estimate


# Confidence per source (0-100). Farmer-entered lab/SHC data ranks highest;
# a farm-registration baseline is low-confidence and clearly marked.
SOURCE_CONFIDENCE: dict[str, int] = {
    SoilSource.LAB.value: 95,
    SoilSource.SOIL_HEALTH_CARD.value: 90,
    SoilSource.GOVERNMENT.value: 80,
    SoilSource.SELF.value: 70,
    SoilSource.SATELLITE.value: 60,
    SoilSource.FARM_REGISTRATION.value: 30,
    SoilSource.ESTIMATE.value: 25,
}


class ReportStatus(StrEnum):
    SUBMITTED = "submitted"
    PROCESSED = "processed"


class RatingLevel(StrEnum):
    """Generic nutrient/level rating."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    OPTIMAL = "optimal"
    UNKNOWN = "unknown"


class PhClass(StrEnum):
    STRONGLY_ACIDIC = "strongly_acidic"
    ACIDIC = "acidic"
    NEUTRAL = "neutral"
    ALKALINE = "alkaline"
    STRONGLY_ALKALINE = "strongly_alkaline"
    UNKNOWN = "unknown"


class DrainageClass(StrEnum):
    POOR = "poor"
    MODERATE = "moderate"
    GOOD = "good"
    EXCESSIVE = "excessive"
    UNKNOWN = "unknown"


class RecommendationCategory(StrEnum):
    PH = "ph"
    ORGANIC_CARBON = "organic_carbon"
    NITROGEN = "nitrogen"
    PHOSPHORUS = "phosphorus"
    POTASSIUM = "potassium"
    MICRONUTRIENT = "micronutrient"
    DRAINAGE = "drainage"
    WATER_HOLDING = "water_holding"
    GENERAL = "general"


class Severity(StrEnum):
    INFO = "info"
    ADVICE = "advice"
    WARNING = "warning"
    CRITICAL = "critical"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Severity ordering (for "worst-parameter" detection + notifications).
SEVERITY_ORDER: dict[str, int] = {
    Severity.INFO.value: 0,
    Severity.ADVICE.value: 1,
    Severity.WARNING.value: 2,
    Severity.CRITICAL.value: 3,
}

# --------------------------------------------------------------------------- #
# Standard agronomic thresholds — Indian Soil Health Card rating bands.
# Transparent + verifiable; NOT fabricated (docs/PRODUCT_RULES.md).
# --------------------------------------------------------------------------- #
# pH
PH_STRONGLY_ACIDIC = 5.5
PH_ACIDIC = 6.5
PH_NEUTRAL_MAX = 7.5
PH_STRONGLY_ALKALINE = 8.5

# Organic carbon (%)
OC_LOW = 0.5
OC_MEDIUM = 0.75

# Available nitrogen (kg/ha)
N_LOW = 280.0
N_MEDIUM = 560.0

# Available phosphorus (kg/ha)
P_LOW = 10.0
P_MEDIUM = 25.0

# Available potassium (kg/ha)
K_LOW = 120.0
K_MEDIUM = 280.0

# Electrical conductivity (dS/m) — salinity flag.
EC_NORMAL = 1.0
EC_HIGH = 2.0

# Micronutrient sufficiency floors (ppm, DTPA) — below = deficient.
MICRONUTRIENT_FLOORS: dict[str, float] = {
    "zinc": 0.6,
    "iron": 4.5,
    "manganese": 2.0,
    "copper": 0.2,
    "boron": 0.5,
}

# Units used when reporting each parameter (client localizes labels).
PARAMETER_UNITS: dict[str, str] = {
    "ph": "",
    "organic_carbon": "%",
    "nitrogen": "kg/ha",
    "phosphorus": "kg/ha",
    "potassium": "kg/ha",
    "ec_salinity": "dS/m",
    "water_holding_capacity": "%",
}
