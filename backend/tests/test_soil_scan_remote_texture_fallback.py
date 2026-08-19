"""SoilGrids remote texture estimate as a fallback inside the main Soil Scan
(docs: app/modules/soil/scan.py's ScanInputs.soil_texture_remote docstring).

Precedence must always be: the farmer's own registered soil type first, the
opt-in SoilGrids global-model estimate second (evidence-tagged AI_ESTIMATED,
never confused with what the farmer told us), and "insufficient data" only
when neither exists. These are pure unit tests against build_scan -- no DB,
no network.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.soil.scan import (
    EvidenceClass,
    EvidenceObservation,
    IndicatorCode,
    ScanInputs,
    build_scan,
)

AOI = {
    "type": "Polygon",
    "coordinates": [[[79.1, 10.7], [79.2, 10.7], [79.2, 10.8], [79.1, 10.8], [79.1, 10.7]]],
}


def _indicator(scan, code: IndicatorCode):
    return next(i for i in scan.indicators if i.code == code)


def test_no_registered_type_and_no_remote_estimate_stays_insufficient() -> None:
    scan = build_scan(ScanInputs(aoi_verified=True, aoi_geojson=AOI))
    ind = _indicator(scan, IndicatorCode.TEXTURE_LIKELIHOOD)
    assert ind.status == "insufficient_data"
    assert ind.evidence_class == EvidenceClass.RISK_INFERRED
    assert ind.explanation_code == "soil.scan.texture_likelihood.insufficient"


def test_remote_soilgrids_estimate_fills_in_when_no_soil_type_registered() -> None:
    remote = EvidenceObservation(
        source="soilgrids",
        observed_at=datetime(2021, 6, 14, tzinfo=UTC),
        freshness="model_estimate",
        quality="usable",
        values={"texture_class": "loamy", "clay_pct": 25.0, "sand_pct": 40.0, "silt_pct": 35.0},
    )
    scan = build_scan(
        ScanInputs(aoi_verified=True, aoi_geojson=AOI, soil_texture_remote=remote)
    )
    ind = _indicator(scan, IndicatorCode.TEXTURE_LIKELIHOOD)
    assert ind.status == "available"
    assert ind.evidence_class == EvidenceClass.AI_ESTIMATED
    assert ind.value == "loamy"
    assert ind.explanation_code == "soil.scan.texture_likelihood.remote_estimate"
    assert ind.details == {"clay_pct": 25.0, "sand_pct": 40.0, "silt_pct": 35.0}
    assert ind.sources == ("soilgrids",)


def test_a_registered_soil_type_always_wins_over_the_remote_estimate() -> None:
    """A farmer's own answer must never be shadowed by a decades-old global
    soil-map model -- even when both are present."""
    remote = EvidenceObservation(
        source="soilgrids",
        observed_at=datetime(2021, 6, 14, tzinfo=UTC),
        freshness="model_estimate",
        quality="usable",
        values={"texture_class": "clay", "clay_pct": 45.0, "sand_pct": 30.0, "silt_pct": 25.0},
    )
    scan = build_scan(
        ScanInputs(
            aoi_verified=True,
            aoi_geojson=AOI,
            soil_type="sandy",
            soil_texture_remote=remote,
        )
    )
    ind = _indicator(scan, IndicatorCode.TEXTURE_LIKELIHOOD)
    assert ind.status == "available"
    assert ind.evidence_class == EvidenceClass.USER_ENTERED
    assert ind.value == "sandy"
    assert ind.explanation_code == "soil.scan.texture_likelihood.farmer_reported"
    assert ind.sources == ("farmer_reported",)


def test_unverified_boundary_still_masks_everything_including_remote_estimate() -> None:
    """aoi_verified=False must still force every indicator to the unavailable
    state -- the remote-texture fallback must not create an exception."""
    remote = EvidenceObservation(
        source="soilgrids",
        observed_at=datetime(2021, 6, 14, tzinfo=UTC),
        freshness="model_estimate",
        quality="usable",
        values={"texture_class": "loamy", "clay_pct": 25.0, "sand_pct": 40.0, "silt_pct": 35.0},
    )
    scan = build_scan(ScanInputs(aoi_verified=False, soil_texture_remote=remote))
    ind = _indicator(scan, IndicatorCode.TEXTURE_LIKELIHOOD)
    assert ind.status == "unavailable"
    assert ind.evidence_class == EvidenceClass.UNAVAILABLE
