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


def test_scan_always_returns_all_eleven_outputs():
    scan = build_scan(ScanInputs(aoi_verified=False))
    assert len(scan.indicators) == 11
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
                    values={"moisture_status": "relatively_dry"},
                    reference="scene-real-1",
                ),
            ),
        )
    )
    moisture = next(i for i in scan.indicators if i.code is IndicatorCode.SOIL_MOISTURE)
    assert moisture.value == "relatively_dry"
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
    assert len(scan.indicators) == 11
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
