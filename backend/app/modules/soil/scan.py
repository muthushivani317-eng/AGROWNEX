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
    ORGANIC_CARBON_ESTIMATE = "organic_carbon_estimate"
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
    # Real, already-measured lab values (SoilProfile.ph / .ec_salinity, when the
    # farmer has ever submitted one) and the farmer-registered soil type. Reusing
    # these here -- rather than leaving ACIDITY_PH_RISK / SALINITY_RISK / TEXTURE_
    # LIKELIHOOD permanently stubbed -- is not new inference: SoilEngine.classify_ph
    # / classify_salinity already run these exact values through the same
    # transparent Soil Health Card thresholds for the dashboard; the scan just
    # hadn't been wired to them (found + fixed 2026-08-17, reported live as "the
    # most important feature" showing "not enough data" across the board).
    soil_ph: EvidenceObservation | None = None  # values={"ph": float, "rating": str}
    soil_ec: EvidenceObservation | None = None  # values={"ec_salinity": float, "rating": str}
    # Opt-in global soil-map fallback (SoilGridsProvider, SOIL_PROVIDER=soilgrids)
    # for when the farmer has never submitted a real lab pH. Precedence 2: a real
    # measured `soil_ph` above always wins and this is never consulted when one
    # exists (service.py only populates this when soil_ph is None). Kept as its
    # own field, evidence-tagged AI_ESTIMATED rather than MEASURED_FROM_REPORT,
    # so a farmer can never mistake a decades-old compiled global model for their
    # own field's lab result (added 2026-08-19, wiring the standalone SoilGrids
    # provider into the main scan rather than only the separate /soil/remote
    # endpoint).
    soil_ph_remote: EvidenceObservation | None = None  # values={"ph": float, "rating": str}
    # Same opt-in SoilGrids fallback, for Texture likelihood -- consulted only
    # when the farmer has never registered a soil type on the farm profile
    # (service.py only populates this when soil_type is falsy), so a farmer's
    # own answer always wins. Also AI_ESTIMATED, never USER_ENTERED, so a
    # global compiled model is never mistaken for what the farmer told us
    # (added 2026-08-19, alongside the pH fallback above).
    # values={"texture_class": str, "clay_pct"/"sand_pct"/"silt_pct": float}
    soil_texture_remote: EvidenceObservation | None = None
    soil_organic_carbon_remote: EvidenceObservation | None = None
    soil_type: str | None = None
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
    # Bug (found 2026-08-17): this matched against {"relatively_wet",
    # "relatively_dry", "uncertain"}, but the satellite engine's real
    # MoistureStatus values are very_dry/dry/adequate/moist/wet/unknown
    # (app/modules/satellite/constants.py) -- none of those strings ever
    # matched, so Soil Moisture silently showed "not enough data" even when a
    # usable satellite session existed for the farm.
    _moisture_statuses = {"very_dry", "dry", "adequate", "moist", "wet"}
    moisture = next(
        (o for o in usable_satellite if o.values.get("moisture_status") in _moisture_statuses),
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
    # Drought / moisture stress: the same satellite moisture reading, but only
    # when it's on the dry side -- a distinct "risk" framing from the neutral
    # Soil Moisture indicator above, using the same real NDMI-derived value.
    drought = next(
        (o for o in usable_satellite if o.values.get("moisture_status") in {"very_dry", "dry"}),
        None,
    )
    if drought is not None:
        by_code[IndicatorCode.DROUGHT_STRESS] = ScanIndicator(
            IndicatorCode.DROUGHT_STRESS,
            "available",
            EvidenceClass.RISK_INFERRED,
            str(drought.values["moisture_status"]),
            "soil.scan.drought_stress.satellite_context",
            {
                "freshness": drought.freshness,
                "quality": drought.quality,
                "vegetation_stress_level": drought.values.get("stress_level"),
            },
            sources=(drought.source,),
            observation_timestamps=(drought.observed_at,),
        )
    # Bare soil / cover: standard NDVI-derived vegetation-health classification
    # from the same satellite session (already computed and shown on the
    # Satellite Intelligence screen) -- low/very-low/bare readings are a real,
    # transparent signal of sparse ground cover, not a new estimate.
    cover = next(
        (
            o
            for o in usable_satellite
            if o.values.get("vegetation_health")
            in {"bare", "very_low", "low", "moderate", "good", "very_good"}
        ),
        None,
    )
    if cover is not None:
        by_code[IndicatorCode.SOIL_COVER] = ScanIndicator(
            IndicatorCode.SOIL_COVER,
            "available",
            EvidenceClass.RISK_INFERRED,
            str(cover.values["vegetation_health"]),
            "soil.scan.soil_cover.satellite_context",
            {"freshness": cover.freshness, "quality": cover.quality},
            sources=(cover.source,),
            observation_timestamps=(cover.observed_at,),
        )
    # Erosion/runoff is a screening result from mapped slope, current ground
    # cover, and recent rainfall. It is deliberately RISK_INFERRED: no claim is
    # made about measured soil loss or a surveyed drainage path.
    terrain = next(
        (
            item
            for item in inputs.terrain
            if item.quality == "usable" and item.values.get("slope_class")
        ),
        None,
    )
    if terrain is not None:
        slope_class = str(terrain.values["slope_class"])
        cover_class = str(cover.values.get("vegetation_health")) if cover is not None else None
        precipitation = next(
            (
                float(item.values["precipitation_mm"])
                for item in inputs.weather
                if item.quality == "usable"
                and isinstance(item.values.get("precipitation_mm"), int | float)
                and not isinstance(item.values.get("precipitation_mm"), bool)
            ),
            None,
        )
        sparse_cover = cover_class in {"bare", "very_low", "low"}
        heavy_rain = precipitation is not None and precipitation >= 10
        if slope_class == "steep" or (slope_class == "moderate" and (sparse_cover or heavy_rain)):
            erosion_value = "higher_attention"
        elif slope_class == "moderate" or sparse_cover or heavy_rain:
            erosion_value = "moderate_attention"
        else:
            erosion_value = "lower_attention"
        observations = [terrain]
        if cover is not None:
            observations.append(cover)
        weather_observation = next(
            (item for item in inputs.weather if item.quality == "usable"), None
        )
        if weather_observation is not None:
            observations.append(weather_observation)
        by_code[IndicatorCode.EROSION_RUNOFF] = ScanIndicator(
            IndicatorCode.EROSION_RUNOFF,
            "available",
            EvidenceClass.RISK_INFERRED,
            erosion_value,
            "soil.scan.erosion_runoff.terrain_screening",
            {
                "slope_class": slope_class,
                "mean_slope_degrees": terrain.values.get("mean_slope_degrees"),
                "elevation_range_m": terrain.values.get("elevation_range_m"),
                "cover_class": cover_class,
                "precipitation_mm": precipitation,
            },
            sources=tuple(dict.fromkeys(item.source for item in observations)),
            observation_timestamps=tuple(item.observed_at for item in observations),
        )
    # Acidity/pH and salinity risk: reuse the farmer's own submitted lab value
    # (already run through SoilEngine.classify_ph / classify_salinity for the
    # dashboard) instead of leaving these permanently stubbed regardless of
    # whether a real measurement exists.
    if inputs.soil_ph is not None:
        by_code[IndicatorCode.ACIDITY_PH_RISK] = ScanIndicator(
            IndicatorCode.ACIDITY_PH_RISK,
            "available",
            EvidenceClass.MEASURED_FROM_REPORT,
            inputs.soil_ph.values.get("rating"),
            "soil.scan.acidity_ph_risk.measured",
            {"ph": inputs.soil_ph.values.get("ph")},
            sources=(inputs.soil_ph.source,),
            observation_timestamps=(inputs.soil_ph.observed_at,),
        )
    elif inputs.soil_ph_remote is not None:
        by_code[IndicatorCode.ACIDITY_PH_RISK] = ScanIndicator(
            IndicatorCode.ACIDITY_PH_RISK,
            "available",
            EvidenceClass.AI_ESTIMATED,
            inputs.soil_ph_remote.values.get("rating"),
            "soil.scan.acidity_ph_risk.remote_estimate",
            {"ph": inputs.soil_ph_remote.values.get("ph")},
            sources=(inputs.soil_ph_remote.source,),
            observation_timestamps=(inputs.soil_ph_remote.observed_at,),
        )
    if inputs.soil_ec is not None:
        by_code[IndicatorCode.SALINITY_RISK] = ScanIndicator(
            IndicatorCode.SALINITY_RISK,
            "available",
            EvidenceClass.MEASURED_FROM_REPORT,
            inputs.soil_ec.values.get("rating"),
            "soil.scan.salinity_risk.measured",
            {"ec_salinity": inputs.soil_ec.values.get("ec_salinity")},
            sources=(inputs.soil_ec.source,),
            observation_timestamps=(inputs.soil_ec.observed_at,),
        )
    # Texture likelihood: the farmer's own registered soil type (farm
    # registration), not a soil-map estimate -- explicitly USER_ENTERED so it's
    # never confused with a measured or remote-sensed value.
    if inputs.soil_type:
        by_code[IndicatorCode.TEXTURE_LIKELIHOOD] = ScanIndicator(
            IndicatorCode.TEXTURE_LIKELIHOOD,
            "available",
            EvidenceClass.USER_ENTERED,
            inputs.soil_type,
            "soil.scan.texture_likelihood.farmer_reported",
            {},
            sources=("farmer_reported",),
        )
    elif inputs.soil_texture_remote is not None:
        by_code[IndicatorCode.TEXTURE_LIKELIHOOD] = ScanIndicator(
            IndicatorCode.TEXTURE_LIKELIHOOD,
            "available",
            EvidenceClass.AI_ESTIMATED,
            inputs.soil_texture_remote.values.get("texture_class"),
            "soil.scan.texture_likelihood.remote_estimate",
            {
                "clay_pct": inputs.soil_texture_remote.values.get("clay_pct"),
                "sand_pct": inputs.soil_texture_remote.values.get("sand_pct"),
                "silt_pct": inputs.soil_texture_remote.values.get("silt_pct"),
            },
            sources=(inputs.soil_texture_remote.source,),
            observation_timestamps=(inputs.soil_texture_remote.observed_at,),
        )
    if inputs.soil_organic_carbon_remote is not None:
        remote_carbon = inputs.soil_organic_carbon_remote
        by_code[IndicatorCode.ORGANIC_CARBON_ESTIMATE] = ScanIndicator(
            IndicatorCode.ORGANIC_CARBON_ESTIMATE,
            "available",
            EvidenceClass.AI_ESTIMATED,
            remote_carbon.values.get("organic_carbon"),
            "soil.scan.organic_carbon_estimate.remote_estimate",
            {
                "unit": "%",
                "uncertainty_low": remote_carbon.values.get("uncertainty_low"),
                "uncertainty_high": remote_carbon.values.get("uncertainty_high"),
                "resolution_m": remote_carbon.values.get("resolution_m"),
            },
            sources=(remote_carbon.source,),
            observation_timestamps=(remote_carbon.observed_at,),
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
