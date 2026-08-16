"""Safe Soil Scan outputs built only from observable, provenance-bearing inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.modules.farms.geo import InvalidPolygonError, extract_ring, validate_ring


class EvidenceClass(str, Enum):
    AI_ESTIMATED = "AI_ESTIMATED"
    RISK_INFERRED = "RISK_INFERRED"
    MEASURED_FROM_REPORT = "MEASURED_FROM_REPORT"
    USER_ENTERED = "USER_ENTERED"
    UNAVAILABLE = "UNAVAILABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class IndicatorCode(str, Enum):
    SOIL_MOISTURE = "soil_moisture"
    WATERLOGGING_DRAINAGE = "waterlogging_drainage"
    DROUGHT_STRESS = "drought_stress"
    EROSION_RUNOFF = "erosion_runoff"
    POOR_PERFORMING_ZONES = "poor_performing_zones"
    SOIL_COVER = "soil_cover"
    TEXTURE_LIKELIHOOD = "texture_likelihood"
    SALINITY_RISK = "salinity_risk"
    ORGANIC_MATTER_TREND = "organic_matter_trend"
    ACIDITY_PH_RISK = "acidity_ph_risk"
    SMART_SAMPLING_NAVIGATOR = "smart_sampling_navigator"


@dataclass(frozen=True)
class SamplingPoint:
    zone_id: str
    longitude: float
    latitude: float
    source: str
    reference: str | None = None
    reason: str = "spatial_variability_zone"
    quality: str = "usable"
    sample_data: bool = False


@dataclass(frozen=True)
class EvidenceObservation:
    source: str
    observed_at: datetime
    freshness: str
    quality: str
    values: dict[str, Any]
    reference: str | None = None


@dataclass(frozen=True)
class SpatialVariabilityZone:
    zone_id: str
    geometry: dict[str, Any]
    variability_class: str
    source: str
    reference: str
    observed_at: datetime
    quality: str
    is_sample: bool = False


@dataclass(frozen=True)
class ScanIndicator:
    code: IndicatorCode
    status: str
    evidence_class: EvidenceClass
    value: str | float | None
    explanation_code: str
    details: dict[str, Any] = field(default_factory=dict)
    sampling_points: tuple[SamplingPoint, ...] = ()
    sources: tuple[str, ...] = ()
    observation_timestamps: tuple[datetime, ...] = ()
    missing_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScanInputs:
    aoi_verified: bool
    aoi_geojson: dict[str, Any] | None = None
    waterlogging_status: str | None = None
    variability_zones: tuple[dict[str, Any], ...] = ()
    spatial_zones: tuple[SpatialVariabilityZone, ...] = ()
    weather: tuple[EvidenceObservation, ...] = ()
    satellite: tuple[EvidenceObservation, ...] = ()
    terrain: tuple[EvidenceObservation, ...] = ()
    history: tuple[EvidenceObservation, ...] = ()
    weather_state: str = "unavailable"
    satellite_state: str = "unavailable"
    terrain_state: str = "unavailable"
    # Clock to stamp SoilScan.generated_at with. Defaults to None (build_scan
    # falls back to the real wall clock) so every existing caller/test that
    # doesn't care about the exact timestamp is unaffected. SoilService passes
    # its own injected clock here so that latest_scan()'s tie-break ordering
    # (generated_at.desc(), created_at.desc()) is actually controllable in
    # tests -- previously build_scan() called datetime.now(UTC) directly,
    # silently ignoring SoilService's injected `now`, so two scans run in the
    # same test (even with deliberately distinct injected clocks 5 minutes
    # apart) could land within the same real wall-clock second and collide on
    # SQLite's truncated timestamp storage, making "latest" nondeterministic
    # (found via a real, reproducing pytest failure post pre-release-audit:
    # test_soil_scan_is_append_only_and_latest_is_farm_scoped).
    now: datetime | None = None


@dataclass(frozen=True)
class SoilScan:
    aoi_verified: bool
    generated_at: datetime
    indicators: tuple[ScanIndicator, ...]
    provider_states: dict[str, str] = field(default_factory=dict)


def _missing(code: IndicatorCode, *, unavailable: bool = False) -> ScanIndicator:
    return ScanIndicator(
        code=code,
        status="unavailable" if unavailable else "insufficient_data",
        evidence_class=(
            EvidenceClass.UNAVAILABLE if unavailable else EvidenceClass.INSUFFICIENT_DATA
        ),
        value=None,
        explanation_code=(
            f"soil.scan.{code.value}." f"{'unavailable' if unavailable else 'insufficient'}"
        ),
        missing_evidence=(code.value,),
    )


def _centroid(geometry: dict[str, Any]) -> tuple[float, float] | None:
    try:
        ring = validate_ring(extract_ring(geometry))
    except (InvalidPolygonError, TypeError, ValueError):
        return None
    return (
        round(sum(p[0] for p in ring) / len(ring), 7),
        round(sum(p[1] for p in ring) / len(ring), 7),
    )


def _point_in_polygon(point: tuple[float, float], geometry: dict[str, Any]) -> bool:
    try:
        ring = validate_ring(extract_ring(geometry))
    except (InvalidPolygonError, TypeError, ValueError):
        return False
    x, y = point
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def build_scan(inputs: ScanInputs) -> SoilScan:
    """Return all outputs; never substitute coordinates, measurements, or rules."""
    items = [_missing(code) for code in IndicatorCode]
    by_code = {item.code: item for item in items}
    by_code[IndicatorCode.EROSION_RUNOFF] = _missing(IndicatorCode.EROSION_RUNOFF, unavailable=True)
    by_code[IndicatorCode.TEXTURE_LIKELIHOOD] = ScanIndicator(
        IndicatorCode.TEXTURE_LIKELIHOOD,
        "insufficient_data",
        EvidenceClass.RISK_INFERRED,
        None,
        "soil.scan.texture_likelihood.insufficient",
    )
    by_code[IndicatorCode.SALINITY_RISK] = ScanIndicator(
        IndicatorCode.SALINITY_RISK,
        "insufficient_data",
        EvidenceClass.RISK_INFERRED,
        None,
        "soil.scan.salinity_risk.insufficient",
    )
    by_code[IndicatorCode.ACIDITY_PH_RISK] = ScanIndicator(
        IndicatorCode.ACIDITY_PH_RISK,
        "insufficient_data",
        EvidenceClass.RISK_INFERRED,
        None,
        "soil.scan.acidity_ph_risk.soil_test_required",
    )
    if inputs.aoi_verified and inputs.waterlogging_status in {
        "clear",
        "possible_waterlogging",
        "review_required",
        "insufficient_data",
    }:
        by_code[IndicatorCode.WATERLOGGING_DRAINAGE] = ScanIndicator(
            IndicatorCode.WATERLOGGING_DRAINAGE,
            "available",
            EvidenceClass.RISK_INFERRED,
            inputs.waterlogging_status,
            "soil.scan.waterlogging_drainage.existing_assessment",
            {"source": "waterlogging_assessment"},
            sources=("waterlogging_assessment",),
        )
    usable_satellite = [o for o in inputs.satellite if o.quality == "usable"]
    moisture = next(
        (
            o
            for o in usable_satellite
            if o.values.get("moisture_status") in {"relatively_wet", "relatively_dry", "uncertain"}
        ),
        None,
    )
    if moisture is not None:
        by_code[IndicatorCode.SOIL_MOISTURE] = ScanIndicator(
            IndicatorCode.SOIL_MOISTURE,
            "available",
            EvidenceClass.RISK_INFERRED,
            str(moisture.values["moisture_status"]),
            "soil.scan.soil_moisture.satellite_context",
            {"freshness": moisture.freshness, "quality": moisture.quality},
            sources=(moisture.source,),
            observation_timestamps=(moisture.observed_at,),
        )
    usable_history = sorted(
        (item for item in inputs.history if item.quality == "usable"),
        key=lambda item: item.observed_at,
    )
    zone_observations = [
        item
        for item in usable_history
        if isinstance(item.values.get("poor_zone_ids"), list) and item.values["poor_zone_ids"]
    ]
    if len({item.observed_at for item in zone_observations}) >= 2:
        repeated = set(zone_observations[0].values["poor_zone_ids"])
        for observation in zone_observations[1:]:
            repeated &= set(observation.values["poor_zone_ids"])
        if repeated:
            by_code[IndicatorCode.POOR_PERFORMING_ZONES] = ScanIndicator(
                IndicatorCode.POOR_PERFORMING_ZONES,
                "available",
                EvidenceClass.RISK_INFERRED,
                "repeated_observation",
                "soil.scan.poor_performing_zones.repeated",
                {
                    "zone_ids": sorted(repeated),
                    "observation_count": len(zone_observations),
                },
                sources=tuple(dict.fromkeys(item.source for item in zone_observations)),
                observation_timestamps=tuple(item.observed_at for item in zone_observations),
            )
    organic_history = [
        item
        for item in usable_history
        if isinstance(item.values.get("organic_carbon"), int | float)
        and not isinstance(item.values.get("organic_carbon"), bool)
    ]
    if len({item.observed_at for item in organic_history}) >= 2:
        first = float(organic_history[0].values["organic_carbon"])
        last = float(organic_history[-1].values["organic_carbon"])
        direction = (
            "improving_direction"
            if last > first
            else "declining_direction"
            if last < first
            else "stable_or_uncertain"
        )
        by_code[IndicatorCode.ORGANIC_MATTER_TREND] = ScanIndicator(
            IndicatorCode.ORGANIC_MATTER_TREND,
            "available",
            EvidenceClass.MEASURED_FROM_REPORT,
            direction,
            "soil.scan.organic_matter_trend.measured_history",
            {"observation_count": len(organic_history)},
            sources=tuple(dict.fromkeys(item.source for item in organic_history)),
            observation_timestamps=tuple(item.observed_at for item in organic_history),
        )
    points: list[SamplingPoint] = []
    if inputs.aoi_verified:
        for zone in inputs.variability_zones:
            centroid = zone.get("centroid")
            if (
                isinstance(zone.get("zone_id"), str)
                and isinstance(zone.get("source"), str)
                and isinstance(centroid, list | tuple)
                and len(centroid) == 2
                and all(isinstance(v, int | float) and not isinstance(v, bool) for v in centroid)
                and -180 <= centroid[0] <= 180
                and -90 <= centroid[1] <= 90
            ):
                points.append(
                    SamplingPoint(
                        zone["zone_id"],
                        float(centroid[0]),
                        float(centroid[1]),
                        zone["source"],
                    )
                )
        if inputs.aoi_geojson:
            for zone in sorted(inputs.spatial_zones, key=lambda item: item.zone_id):
                centroid = _centroid(zone.geometry)
                if (
                    zone.is_sample
                    or zone.quality != "usable"
                    or not zone.reference
                    or centroid is None
                    or not _point_in_polygon(centroid, inputs.aoi_geojson)
                ):
                    continue
                if any(
                    abs(p.longitude - centroid[0]) < 1e-7 and abs(p.latitude - centroid[1]) < 1e-7
                    for p in points
                ):
                    continue
                points.append(
                    SamplingPoint(
                        zone.zone_id,
                        centroid[0],
                        centroid[1],
                        zone.source,
                        zone.reference,
                        f"spatial_variability:{zone.variability_class}",
                        zone.quality,
                    )
                )
    if points:
        by_code[IndicatorCode.SMART_SAMPLING_NAVIGATOR] = ScanIndicator(
            IndicatorCode.SMART_SAMPLING_NAVIGATOR,
            "available",
            EvidenceClass.AI_ESTIMATED,
            None,
            "soil.scan.smart_sampling_navigator.variability_based",
            {"method": "zone_centroid", "point_count": len(points)},
            tuple(points),
            sources=tuple(dict.fromkeys(point.source for point in points)),
        )
    if not inputs.aoi_verified:
        by_code = {code: _missing(code, unavailable=True) for code in IndicatorCode}
    return SoilScan(
        inputs.aoi_verified,
        inputs.now or datetime.now(UTC),
        tuple(by_code[code] for code in IndicatorCode),
        {
            "weather": inputs.weather_state,
            "satellite": inputs.satellite_state,
            "terrain": inputs.terrain_state,
        },
    )
