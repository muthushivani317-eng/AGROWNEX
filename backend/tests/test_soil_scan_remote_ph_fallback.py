"""SoilGrids remote pH estimate as a fallback inside the main Soil Scan
(docs: app/modules/soil/scan.py's ScanInputs.soil_ph_remote docstring).

Precedence must always be: a real farmer-submitted lab pH first, the opt-in
SoilGrids global-model estimate second (evidence-tagged AI_ESTIMATED, never
confused with a real measurement), and "insufficient data" only when neither
exists. These are pure unit tests against build_scan -- no DB, no network.
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


def test_no_measured_and_no_remote_ph_stays_insufficient() -> None:
    scan = build_scan(ScanInputs(aoi_verified=True, aoi_geojson=AOI))
    ind = _indicator(scan, IndicatorCode.ACIDITY_PH_RISK)
    assert ind.status == "insufficient_data"
    assert ind.evidence_class == EvidenceClass.RISK_INFERRED
    assert ind.explanation_code == "soil.scan.acidity_ph_risk.soil_test_required"


def test_remote_soilgrids_estimate_fills_in_when_no_lab_report_exists() -> None:
    remote = EvidenceObservation(
        source="soilgrids",
        observed_at=datetime(2021, 6, 14, tzinfo=UTC),
        freshness="model_estimate",
        quality="usable",
        values={"ph": 6.5, "rating": "slightly_acidic"},
    )
    scan = build_scan(ScanInputs(aoi_verified=True, aoi_geojson=AOI, soil_ph_remote=remote))
    ind = _indicator(scan, IndicatorCode.ACIDITY_PH_RISK)
    assert ind.status == "available"
    assert ind.evidence_class == EvidenceClass.AI_ESTIMATED
    assert ind.value == "slightly_acidic"
    assert ind.explanation_code == "soil.scan.acidity_ph_risk.remote_estimate"
    assert ind.details["ph"] == 6.5
    assert ind.sources == ("soilgrids",)


def test_a_real_measured_ph_always_wins_over_the_remote_estimate() -> None:
    """A farmer's own lab result must never be shadowed by a decades-old global
    soil-map model -- even when both are present."""
    measured = EvidenceObservation(
        source="lab",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        freshness="reported",
        quality="usable",
        values={"ph": 7.0, "rating": "neutral"},
    )
    remote = EvidenceObservation(
        source="soilgrids",
        observed_at=datetime(2021, 6, 14, tzinfo=UTC),
        freshness="model_estimate",
        quality="usable",
        values={"ph": 6.5, "rating": "slightly_acidic"},
    )
    scan = build_scan(
        ScanInputs(aoi_verified=True, aoi_geojson=AOI, soil_ph=measured, soil_ph_remote=remote)
    )
    ind = _indicator(scan, IndicatorCode.ACIDITY_PH_RISK)
    assert ind.status == "available"
    assert ind.evidence_class == EvidenceClass.MEASURED_FROM_REPORT
    assert ind.value == "neutral"
    assert ind.explanation_code == "soil.scan.acidity_ph_risk.measured"
    assert ind.sources == ("lab",)


def test_unverified_boundary_still_masks_everything_including_remote_estimate() -> None:
    """aoi_verified=False must still force every indicator to the unavailable
    state -- the remote-pH fallback must not create an exception to that rule."""
    remote = EvidenceObservation(
        source="soilgrids",
        observed_at=datetime(2021, 6, 14, tzinfo=UTC),
        freshness="model_estimate",
        quality="usable",
        values={"ph": 6.5, "rating": "slightly_acidic"},
    )
    scan = build_scan(ScanInputs(aoi_verified=False, soil_ph_remote=remote))
    ind = _indicator(scan, IndicatorCode.ACIDITY_PH_RISK)
    assert ind.status == "unavailable"
    assert ind.evidence_class == EvidenceClass.UNAVAILABLE
