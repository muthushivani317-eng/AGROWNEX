"""Satellite Intelligence constants (docs: never fabricate satellite data).

A professional farm-monitoring engine over FREE Sentinel-2 imagery. Vegetation
indices and classifications use transparent, standard remote-sensing formulas and
thresholds so results are reproducible. When imagery is genuinely unavailable
(cloud cover, acquisition delay, provider issue, or no farm polygon) the session is
marked *unavailable* with an honest reason — never invented values.
"""
from __future__ import annotations

import os
from enum import StrEnum

DEFAULT_LANGUAGE = "ta"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Provider selection — default is the Sentinel seam (returns "not available" until
# credentials are wired). Set SATELLITE_PROVIDER=mock for a dev/sample provider.
SATELLITE_PROVIDER = os.getenv("SATELLITE_PROVIDER", "")


class SatelliteProviderName(StrEnum):
    SENTINEL = "sentinel"          # Sentinel-2 via Copernicus Data Space (free)
    MOCK = "mock"                  # deterministic dev/sample provider (flagged)
    SENTINEL_HUB = "sentinel_hub"  # future
    COPERNICUS = "copernicus"      # future
    PLANET = "planet"              # future
    MAXAR = "maxar"                # future
    EARTH_ENGINE = "earth_engine"  # future
    PLANETARY_COMPUTER = "planetary_computer"  # future


class SessionStatus(StrEnum):
    AVAILABLE = "available"        # a usable scene was analysed
    UNAVAILABLE = "unavailable"    # honest "Not Available"
    PENDING = "pending"            # acquisition requested, not yet returned


class UnavailableReason(StrEnum):
    NONE = "none"
    NO_POLYGON = "no_polygon"           # farm has no boundary polygon
    CLOUD_COVER = "cloud_cover"         # scene too cloudy to use
    ACQUISITION_DELAY = "acquisition_delay"  # no recent pass yet
    PROVIDER_ERROR = "provider_error"   # provider failed / not configured
    NO_IMAGERY = "no_imagery"           # no scene for the range


class VegetationHealth(StrEnum):
    BARE = "bare"
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    GOOD = "good"
    VERY_GOOD = "very_good"
    UNKNOWN = "unknown"


class StressLevel(StrEnum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class MoistureStatus(StrEnum):
    VERY_DRY = "very_dry"
    DRY = "dry"
    ADEQUATE = "adequate"
    MOIST = "moist"
    WET = "wet"
    UNKNOWN = "unknown"


class HealthTrend(StrEnum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    UNKNOWN = "unknown"


class IndexName(StrEnum):
    NDVI = "ndvi"
    NDRE = "ndre"
    EVI = "evi"
    NDMI = "ndmi"


class SatelliteBand(StrEnum):
    """Rendered image layers (image_url per band)."""

    TRUE_COLOR = "true_color"
    NDVI = "ndvi"
    NDRE = "ndre"
    NDMI = "ndmi"
    MOISTURE = "moisture"


class AlertCategory(StrEnum):
    VEGETATION = "vegetation"
    MOISTURE = "moisture"
    IMAGERY = "imagery"
    VARIATION = "variation"
    SEASONAL = "seasonal"


class Severity(StrEnum):
    INFO = "info"
    ADVICE = "advice"
    WARNING = "warning"
    CRITICAL = "critical"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


SEVERITY_ORDER: dict[str, int] = {
    Severity.INFO.value: 0,
    Severity.ADVICE.value: 1,
    Severity.WARNING.value: 2,
    Severity.CRITICAL.value: 3,
}

# Timeline aggregation ranges.
TIMELINE_WEEKLY = "weekly"
TIMELINE_MONTHLY = "monthly"

# --------------------------------------------------------------------------- #
# Transparent thresholds (standard remote-sensing bands).
# --------------------------------------------------------------------------- #
# NDVI → vegetation health
NDVI_BARE = 0.1
NDVI_VERY_LOW = 0.2
NDVI_LOW = 0.4
NDVI_MODERATE = 0.6
NDVI_GOOD = 0.8

# NDMI → moisture status
NDMI_VERY_DRY = -0.2
NDMI_DRY = 0.0
NDMI_ADEQUATE = 0.2
NDMI_MOIST = 0.4

# Trend / stress detection (NDVI deltas between consecutive sessions)
NDVI_DELTA_IMPROVING = 0.05
NDVI_DELTA_DECLINING = -0.05
NDVI_DELTA_RAPID_DROP = -0.15
NDVI_DELTA_ABNORMAL = -0.20

# Low-vigor + moisture-stress flags
NDVI_LOW_VIGOR = 0.3
NDMI_MOISTURE_STRESS = 0.0

# Field variation (per-index standard deviation) that flags heterogeneity
NDVI_VARIATION_STD = 0.15

# Cloud cover (%)
CLOUD_ADVISORY = 25.0   # partial obstruction → advisory
CLOUD_USABLE_MAX = 40.0  # above this the scene is unusable → unavailable

# How far back the provider looks for a recent pass (days).
ACQUISITION_LOOKBACK_DAYS = 14
