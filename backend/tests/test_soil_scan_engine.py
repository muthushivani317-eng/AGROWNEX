from datetime import UTC, datetime

from app.modules.soil.scan import (
    EvidenceClass,
    EvidenceObservation,
    IndicatorCode,
    ScanInputs,
    SpatialVariabilityZone,
    build_scan,
)


def _result(code: IndicatorCode, **kwargs):
    scan = build_scan(ScanInputs(aoi_verified=True, **kwargs))
    return next(item for item in scan.indicators if item.code is code)


def test_scan_always_returns_all_twelve_outputs():
    scan = build_scan(ScanInputs(aoi_verified=False))
    assert len(scan.indicators) == 12
    assert {item.code for item in scan.indicators} == set(IndicatorCode)


def test_soil_moisture_is_not_fabricated():
    item = _result(IndicatorCode.SOIL_MOISTURE)
    assert item.status == "insufficient_data" and item.value is None


def test_waterlogging_uses_existing_evidence_only():
    item = _result(IndicatorCode.WATERLOGGING_DRAINAGE, waterlogging_status="clear")
    assert item.status == "available" and item.value == "clear"


def test_drought_stress_is_safe_without_verified_rule():
    assert _result(IndicatorCode.DROUGHT_STRESS).status == "insufficient_data"


def test_erosion_is_unavailable_without_terrain():
    assert _result(IndicatorCode.EROSION_RUNOFF).status == "unavailable"


def test_erosion_screening_combines_real_terrain_cover_and_rainfall() -> None:
    observed = datetime(2026, 8, 20, tzinfo=UTC)
    item = _result(
        IndicatorCode.EROSION_RUNOFF,
        terrain=(
            EvidenceObservation(
                "open_meteo_elevation",
                observed,
                "mapped_elevation",
                "usable",
                {"slope_class": "moderate", "mean_slope_degrees": 7.1, "elevation_range_m": 18},
            ),
        ),
        satellite=(
            EvidenceObservation(
                "copernicus",
                observed,
                "current",
                "usable",
                {"vegetation_health": "bare"},
            ),
        ),
        weather=(
            EvidenceObservation(
                "open_meteo",
                observed,
                "current",
                "usable",
                {"precipitation_mm": 12.0},
            ),
        ),
    )
    assert item.status == "available"
    assert item.value == "higher_attention"
    assert item.evidence_class is EvidenceClass.RISK_INFERRED
    assert item.details["mean_slope_degrees"] == 7.1


def test_poor_zones_require_history():
    assert _result(IndicatorCode.POOR_PERFORMING_ZONES).status == "insufficient_data"


def test_soil_cover_requires_observation():
    assert _result(IndicatorCode.SOIL_COVER).value is None


def test_texture_is_likelihood_not_measurement():
    item = _result(IndicatorCode.TEXTURE_LIKELIHOOD)
    assert item.evidence_class is EvidenceClass.RISK_INFERRED


def test_salinity_never_returns_remote_ec():
    item = _result(IndicatorCode.SALINITY_RISK)
    assert item.value is None and "ec" not in item.details


def test_organic_matter_trend_requires_repeated_observations():
    assert _result(IndicatorCode.ORGANIC_MATTER_TREND).status == "insufficient_data"


def test_remote_organic_carbon_is_estimated_not_measured() -> None:
    observed = datetime(2021, 6, 14, tzinfo=UTC)
    item = _result(
        IndicatorCode.ORGANIC_CARBON_ESTIMATE,
        soil_organic_carbon_remote=EvidenceObservation(
            "soilgrids",
            observed,
            "model_estimate",
            "usable",
            {
                "organic_carbon": 1.8,
                "uncertainty_low": 0.8,
                "uncertainty_high": 3.1,
                "resolution_m": 250.0,
            },
        ),
    )
    assert item.value == 1.8
    assert item.evidence_class is EvidenceClass.AI_ESTIMATED
    assert item.details["unit"] == "%"


def test_acidity_is_risk_only_and_has_no_numeric_ph():
    item = _result(IndicatorCode.ACIDITY_PH_RISK)
    assert item.evidence_class is EvidenceClass.RISK_INFERRED and item.value is None


def test_sampling_has_no_static_or_mock_points():
    item = _result(IndicatorCode.SMART_SAMPLING_NAVIGATOR)
    assert item.status == "insufficient_data" and item.sampling_points == ()


def test_sampling_points_derive_only_from_real_variability_zones():
    zones = (
        {"zone_id": "real-a", "centroid": [78.1, 11.1], "source": "sentinel-2"},
        {"zone_id": "real-b", "centroid": [78.2, 11.2], "source": "sentinel-2"},
    )
    item = _result(IndicatorCode.SMART_SAMPLING_NAVIGATOR, variability_zones=zones)
    assert item.status == "available"
    assert [point.zone_id for point in item.sampling_points] == ["real-a", "real-b"]
    assert all(point.sample_data is False for point in item.sampling_points)


def test_invalid_aoi_blocks_every_remote_output():
    scan = build_scan(ScanInputs(aoi_verified=False, waterlogging_status="clear"))
    assert all(item.status in {"unavailable", "insufficient_data"} for item in scan.indicators)


def test_weather_and_satellite_are_provenance_bearing_partial_evidence():
    observed = datetime(2026, 8, 15, tzinfo=UTC)
    scan = build_scan(
        ScanInputs(
            aoi_verified=True,
            weather=(
                EvidenceObservation(
                    source="open-meteo",
                    observed_at=observed,
                    freshness="live",
                    quality="usable",
                    values={"precipitation_mm": 4.0},
                ),
            ),
            satellite=(
                EvidenceObservation(
                    source="copernicus-sentinel-2-l2a",
                    observed_at=observed,
                    freshness="current",
                    quality="usable",
                    # Real MoistureStatus values (app/modules/satellite/constants.py)
                    # are very_dry/dry/adequate/moist/wet -- "relatively_dry" here
                    # was a stale fixture value that never matched the engine's
                    # actual output, silently masking the SOIL_MOISTURE matching
                    # bug fixed 2026-08-17 (see build_scan's _MOISTURE_STATUSES).
                    values={"moisture_status": "dry"},
                    reference="scene-real-1",
                ),
            ),
        )
    )
    moisture = next(i for i in scan.indicators if i.code is IndicatorCode.SOIL_MOISTURE)
    assert moisture.value == "dry"
    assert moisture.evidence_class is EvidenceClass.RISK_INFERRED
    assert moisture.sources == ("copernicus-sentinel-2-l2a",)
    assert moisture.observation_timestamps == (observed,)
    assert "laboratory" not in moisture.details


def test_weather_unavailable_does_not_fail_whole_scan():
    scan = build_scan(
        ScanInputs(
            aoi_verified=True,
            weather_state="unavailable",
            satellite_state="available",
        )
    )
    assert len(scan.indicators) == 12
    assert scan.provider_states["weather"] == "unavailable"


def test_real_spatial_zones_generate_deterministic_inside_aoi_points():
    aoi = {
        "type": "Polygon",
        "coordinates": [[[78.0, 11.0], [78.3, 11.0], [78.3, 11.3], [78.0, 11.3], [78.0, 11.0]]],
    }
    observed = datetime(2026, 8, 15, tzinfo=UTC)
    zones = (
        SpatialVariabilityZone(
            zone_id="z-b",
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [[78.2, 11.2], [78.25, 11.2], [78.25, 11.25], [78.2, 11.25], [78.2, 11.2]]
                ],
            },
            variability_class="higher_variability",
            source="copernicus-sentinel-2-l2a",
            reference="scene-real-1",
            observed_at=observed,
            quality="usable",
            is_sample=False,
        ),
        SpatialVariabilityZone(
            zone_id="z-a",
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [[78.05, 11.05], [78.1, 11.05], [78.1, 11.1], [78.05, 11.1], [78.05, 11.05]]
                ],
            },
            variability_class="lower_variability",
            source="copernicus-sentinel-2-l2a",
            reference="scene-real-1",
            observed_at=observed,
            quality="usable",
            is_sample=False,
        ),
    )
    item = next(
        i
        for i in build_scan(
            ScanInputs(aoi_verified=True, aoi_geojson=aoi, spatial_zones=zones)
        ).indicators
        if i.code is IndicatorCode.SMART_SAMPLING_NAVIGATOR
    )
    assert [p.zone_id for p in item.sampling_points] == ["z-a", "z-b"]
    assert [(p.longitude, p.latitude) for p in item.sampling_points] == [
        (78.075, 11.075),
        (78.225, 11.225),
    ]
    assert all(p.reference == "scene-real-1" for p in item.sampling_points)


def test_sample_or_outside_spatial_zones_never_generate_points():
    aoi = {
        "type": "Polygon",
        "coordinates": [[[78.0, 11.0], [78.2, 11.0], [78.2, 11.2], [78.0, 11.2], [78.0, 11.0]]],
    }
    observed = datetime(2026, 8, 15, tzinfo=UTC)
    zones = (
        SpatialVariabilityZone(
            "sample", aoi, "different", "mock", "fixture", observed, "usable", True
        ),
        SpatialVariabilityZone(
            "outside",
            {
                "type": "Polygon",
                "coordinates": [
                    [[79.0, 12.0], [79.1, 12.0], [79.1, 12.1], [79.0, 12.1], [79.0, 12.0]]
                ],
            },
            "different",
            "copernicus",
            "real-scene",
            observed,
            "usable",
            False,
        ),
    )
    item = next(
        i
        for i in build_scan(
            ScanInputs(aoi_verified=True, aoi_geojson=aoi, spatial_zones=zones)
        ).indicators
        if i.code is IndicatorCode.SMART_SAMPLING_NAVIGATOR
    )
    assert item.status == "insufficient_data"
    assert item.sampling_points == ()


def test_repeated_zone_requires_two_temporally_distinct_observations():
    history = (
        EvidenceObservation(
            "copernicus",
            datetime(2026, 7, 1, tzinfo=UTC),
            "current",
            "usable",
            {"poor_zone_ids": ["z1", "z2"]},
            "scene-1",
        ),
        EvidenceObservation(
            "copernicus",
            datetime(2026, 8, 1, tzinfo=UTC),
            "current",
            "usable",
            {"poor_zone_ids": ["z1"]},
            "scene-2",
        ),
    )
    item = _result(IndicatorCode.POOR_PERFORMING_ZONES, history=history)
    assert item.value == "repeated_observation"
    assert item.details["zone_ids"] == ["z1"]
    assert item.details["observation_count"] == 2


def test_acidity_uses_real_submitted_ph():
    # 2026-08-17: ACIDITY_PH_RISK was permanently stubbed regardless of whether
    # the farmer had ever submitted a real lab pH -- now it reuses the exact
    # same Soil Health Card classification SoilEngine.classify_ph already
    # applies for the dashboard, so a real measured value isn't discarded.
    observed = datetime(2026, 8, 10, tzinfo=UTC)
    item = _result(
        IndicatorCode.ACIDITY_PH_RISK,
        soil_ph=EvidenceObservation(
            source="lab",
            observed_at=observed,
            freshness="reported",
            quality="usable",
            values={"ph": 5.0, "rating": "strongly_acidic"},
        ),
    )
    assert item.status == "available"
    assert item.evidence_class is EvidenceClass.MEASURED_FROM_REPORT
    assert item.value == "strongly_acidic"
    assert item.details["ph"] == 5.0
    assert item.sources == ("lab",)


def test_acidity_stays_insufficient_without_a_submitted_ph():
    assert _result(IndicatorCode.ACIDITY_PH_RISK).status == "insufficient_data"


def test_salinity_uses_real_submitted_ec():
    observed = datetime(2026, 8, 10, tzinfo=UTC)
    item = _result(
        IndicatorCode.SALINITY_RISK,
        soil_ec=EvidenceObservation(
            source="self",
            observed_at=observed,
            freshness="reported",
            quality="usable",
            values={"ec_salinity": 2.5, "rating": "high"},
        ),
    )
    assert item.status == "available"
    assert item.evidence_class is EvidenceClass.MEASURED_FROM_REPORT
    assert item.value == "high"
    assert item.details["ec_salinity"] == 2.5


def test_texture_uses_farmer_reported_soil_type():
    # Farm-registration soil_type is USER_ENTERED, not RISK_INFERRED -- distinct
    # from the "no data at all" stub (test_texture_is_likelihood_not_measurement).
    item = _result(IndicatorCode.TEXTURE_LIKELIHOOD, soil_type="Sandy loam")
    assert item.status == "available"
    assert item.evidence_class is EvidenceClass.USER_ENTERED
    assert item.value == "Sandy loam"


def test_soil_cover_uses_satellite_vegetation_health():
    observed = datetime(2026, 8, 10, tzinfo=UTC)
    item = _result(
        IndicatorCode.SOIL_COVER,
        satellite=(
            EvidenceObservation(
                source="copernicus-sentinel-2-l2a",
                observed_at=observed,
                freshness="current",
                quality="usable",
                values={"vegetation_health": "very_low"},
            ),
        ),
    )
    assert item.status == "available"
    assert item.evidence_class is EvidenceClass.RISK_INFERRED
    assert item.value == "very_low"


def test_drought_stress_available_when_satellite_shows_dry_moisture():
    observed = datetime(2026, 8, 10, tzinfo=UTC)
    item = _result(
        IndicatorCode.DROUGHT_STRESS,
        satellite=(
            EvidenceObservation(
                source="copernicus-sentinel-2-l2a",
                observed_at=observed,
                freshness="current",
                quality="usable",
                values={"moisture_status": "very_dry", "stress_level": "severe"},
            ),
        ),
    )
    assert item.status == "available"
    assert item.value == "very_dry"
    assert item.details["vegetation_stress_level"] == "severe"


def test_drought_stress_stays_insufficient_when_moisture_is_adequate():
    # Adequate moisture still lights up SOIL_MOISTURE (a neutral reading) but
    # must not trigger the DROUGHT_STRESS *risk* framing.
    observed = datetime(2026, 8, 10, tzinfo=UTC)
    scan = build_scan(
        ScanInputs(
            aoi_verified=True,
            satellite=(
                EvidenceObservation(
                    source="copernicus-sentinel-2-l2a",
                    observed_at=observed,
                    freshness="current",
                    quality="usable",
                    values={"moisture_status": "adequate"},
                ),
            ),
        )
    )
    moisture = next(i for i in scan.indicators if i.code is IndicatorCode.SOIL_MOISTURE)
    drought = next(i for i in scan.indicators if i.code is IndicatorCode.DROUGHT_STRESS)
    assert moisture.status == "available"
    assert drought.status == "insufficient_data"


def test_organic_matter_direction_requires_two_measured_history_values():
    history = (
        EvidenceObservation(
            "soil-report",
            datetime(2026, 7, 1, tzinfo=UTC),
            "current",
            "usable",
            {"organic_carbon": 0.4},
            "report-1",
        ),
        EvidenceObservation(
            "soil-report",
            datetime(2026, 8, 1, tzinfo=UTC),
            "current",
            "usable",
            {"organic_carbon": 0.5},
            "report-2",
        ),
    )
    item = _result(IndicatorCode.ORGANIC_MATTER_TREND, history=history)
    assert item.value == "improving_direction"
    assert item.evidence_class is EvidenceClass.MEASURED_FROM_REPORT
    assert "percentage" not in item.details
