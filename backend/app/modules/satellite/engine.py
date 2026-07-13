"""Satellite Engine (docs: Repository → Service → Satellite Engine → Provider).

Pure, deterministic and fully unit-tested. Computes the standard vegetation indices
(NDVI, NDRE, EVI, NDMI) from band reflectances, classifies vegetation health /
stress / moisture against transparent thresholds, and derives the trend from the
previous session. It never invents a missing value: if a required band is absent
the index is ``None`` and the classification is ``unknown`` (docs/PRODUCT_RULES.md).
No I/O, no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean, pstdev

from app.modules.satellite.constants import (
    NDMI_ADEQUATE,
    NDMI_DRY,
    NDMI_MOIST,
    NDMI_VERY_DRY,
    NDVI_BARE,
    NDVI_DELTA_DECLINING,
    NDVI_DELTA_IMPROVING,
    NDVI_DELTA_RAPID_DROP,
    NDVI_GOOD,
    NDVI_LOW,
    NDVI_MODERATE,
    NDVI_VERY_LOW,
    HealthTrend,
    MoistureStatus,
    StressLevel,
    VegetationHealth,
)


@dataclass(frozen=True)
class BandReflectance:
    """Mean surface reflectance (0-1) for the field. Any band may be ``None``.

    Sentinel-2: red=B4, nir=B8, red_edge=B5, swir=B11, blue=B2.
    """

    red: float | None = None
    nir: float | None = None
    red_edge: float | None = None
    swir: float | None = None
    blue: float | None = None


@dataclass(frozen=True)
class IndexValues:
    ndvi: float | None = None
    ndre: float | None = None
    evi: float | None = None
    ndmi: float | None = None


@dataclass(frozen=True)
class SatelliteAssessment:
    ndvi: float | None
    ndre: float | None
    evi: float | None
    ndmi: float | None
    vegetation_health: str
    stress_level: str
    moisture_status: str
    trend: str
    ndvi_delta: float | None
    has_values: bool


def _ratio(a: float | None, b: float | None) -> float | None:
    """(a - b) / (a + b), guarding division by zero. ``None`` if inputs missing."""
    if a is None or b is None:
        return None
    denom = a + b
    if denom == 0:
        return None
    return round((a - b) / denom, 4)


def compute_ndvi(bands: BandReflectance) -> float | None:
    return _ratio(bands.nir, bands.red)


def compute_ndre(bands: BandReflectance) -> float | None:
    return _ratio(bands.nir, bands.red_edge)


def compute_ndmi(bands: BandReflectance) -> float | None:
    return _ratio(bands.nir, bands.swir)


def compute_evi(bands: BandReflectance) -> float | None:
    if bands.nir is None or bands.red is None or bands.blue is None:
        return None
    denom = bands.nir + 6 * bands.red - 7.5 * bands.blue + 1
    if denom == 0:
        return None
    return round(2.5 * (bands.nir - bands.red) / denom, 4)


def compute_indices(bands: BandReflectance) -> IndexValues:
    return IndexValues(
        ndvi=compute_ndvi(bands),
        ndre=compute_ndre(bands),
        evi=compute_evi(bands),
        ndmi=compute_ndmi(bands),
    )


def index_stats(samples: list[float]) -> tuple[float, float, float, float] | None:
    """(mean, min, max, std) from per-pixel samples, or ``None`` if empty."""
    values = [v for v in samples if v is not None]
    if not values:
        return None
    return (
        round(fmean(values), 4),
        round(min(values), 4),
        round(max(values), 4),
        round(pstdev(values), 4) if len(values) > 1 else 0.0,
    )


# --------------------------------------------------------------------------- #
# Classifiers (pure)
# --------------------------------------------------------------------------- #
def classify_health(ndvi: float | None) -> str:
    if ndvi is None:
        return VegetationHealth.UNKNOWN.value
    if ndvi < NDVI_BARE:
        return VegetationHealth.BARE.value
    if ndvi < NDVI_VERY_LOW:
        return VegetationHealth.VERY_LOW.value
    if ndvi < NDVI_LOW:
        return VegetationHealth.LOW.value
    if ndvi < NDVI_MODERATE:
        return VegetationHealth.MODERATE.value
    if ndvi < NDVI_GOOD:
        return VegetationHealth.GOOD.value
    return VegetationHealth.VERY_GOOD.value


def classify_moisture(ndmi: float | None) -> str:
    if ndmi is None:
        return MoistureStatus.UNKNOWN.value
    if ndmi < NDMI_VERY_DRY:
        return MoistureStatus.VERY_DRY.value
    if ndmi < NDMI_DRY:
        return MoistureStatus.DRY.value
    if ndmi < NDMI_ADEQUATE:
        return MoistureStatus.ADEQUATE.value
    if ndmi < NDMI_MOIST:
        return MoistureStatus.MOIST.value
    return MoistureStatus.WET.value


def classify_trend(ndvi: float | None, previous_ndvi: float | None) -> tuple[str, float | None]:
    if ndvi is None or previous_ndvi is None:
        return HealthTrend.UNKNOWN.value, None
    delta = round(ndvi - previous_ndvi, 4)
    if delta >= NDVI_DELTA_IMPROVING:
        return HealthTrend.IMPROVING.value, delta
    if delta <= NDVI_DELTA_DECLINING:
        return HealthTrend.DECLINING.value, delta
    return HealthTrend.STABLE.value, delta


def classify_stress(ndvi: float | None, trend: str, delta: float | None) -> str:
    if ndvi is None:
        return StressLevel.UNKNOWN.value
    if ndvi < NDVI_VERY_LOW:
        base = StressLevel.SEVERE.value
    elif ndvi < NDVI_LOW:
        base = StressLevel.MODERATE.value
    elif ndvi < NDVI_MODERATE:
        base = StressLevel.MILD.value
    else:
        base = StressLevel.NONE.value
    # A rapid decline raises the stress by one level.
    if delta is not None and delta <= NDVI_DELTA_RAPID_DROP:
        order = [
            StressLevel.NONE.value, StressLevel.MILD.value,
            StressLevel.MODERATE.value, StressLevel.SEVERE.value,
        ]
        base = order[min(order.index(base) + 1, len(order) - 1)]
    elif trend == HealthTrend.DECLINING.value and base == StressLevel.NONE.value:
        base = StressLevel.MILD.value
    return base


def assess(indices: IndexValues, previous_ndvi: float | None = None) -> SatelliteAssessment:
    """Classify a scene's indices (pure). ``unknown`` where a value is missing."""
    trend, delta = classify_trend(indices.ndvi, previous_ndvi)
    has_values = any(
        v is not None for v in (indices.ndvi, indices.ndre, indices.evi, indices.ndmi)
    )
    return SatelliteAssessment(
        ndvi=indices.ndvi,
        ndre=indices.ndre,
        evi=indices.evi,
        ndmi=indices.ndmi,
        vegetation_health=classify_health(indices.ndvi),
        stress_level=classify_stress(indices.ndvi, trend, delta),
        moisture_status=classify_moisture(indices.ndmi),
        trend=trend,
        ndvi_delta=delta,
        has_values=has_values,
    )


def compute_confidence(cloud_cover: float | None, *, is_sample: bool = False) -> int:
    """Data-reliability score (0-100) from cloud cover. Sample data is capped."""
    if cloud_cover is None:
        base = 50
    else:
        base = max(10, min(99, round(100 - cloud_cover * 1.5)))
    return min(base, 55) if is_sample else base
