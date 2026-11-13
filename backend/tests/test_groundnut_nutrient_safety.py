from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.modules.nutrient.schemas import NutrientReportOut


def _report(*, crop: str = "Groundnut", primary: str | None = "nitrogen", status: str = "confirmed"):
    analysis = SimpleNamespace(
        primary_deficiency=primary,
        secondary_deficiency="zinc" if primary else None,
        status=status,
        confidence=91,
        severity="moderate",
        affected_area="widespread",
        disease_conflict=False,
        needs_test=False,
        needs_expert=False,
        soil_reference={"has_data": True, "macro_ratings": {"nitrogen": "low"}},
        satellite_reference=None,
        weather_reference=None,
        explanation_tamil="specific provider claim",
        explanation_english="specific provider claim",
    )
    remedy = SimpleNamespace(
        category="nutrient",
        code="nutrient.rec.nitrogen.deficiency",
        nutrient="nitrogen",
        severity="warning",
        priority="medium",
    )
    return SimpleNamespace(
        id=uuid4(), farm_id=uuid4(), crop=crop, image_url="private://leaf.jpg",
        thumbnail_url=None, capture_date=None, provider="gemini", model_used="vision",
        status="analyzed", language="en", latitude=None, longitude=None,
        weather_snapshot=None, analysis=analysis, symptoms=[], recommendations=[remedy],
        created_at=datetime.now(UTC),
    )


def test_groundnut_specific_finding_is_never_confirmed_or_calibrated() -> None:
    out = NutrientReportOut.from_report(_report())
    assert out.analysis is not None
    assert out.analysis.status == "possible"
    assert out.analysis.confidence is None
    assert out.analysis.confidence_band is None
    assert out.analysis.expert_verified is False
    assert out.analysis.needs_test is True
    assert out.analysis.needs_expert is True
    assert out.analysis.suggested_next_evidence == ["soil_or_tissue_test", "expert_review"]


def test_groundnut_suppresses_remedies_and_requires_test_and_expert_actions() -> None:
    out = NutrientReportOut.from_report(_report())
    assert [r.category for r in out.recommendations] == ["test", "expert"]
    assert all(r.nutrient is None for r in out.recommendations)
    assert out.analysis is not None
    assert out.analysis.explanation_english is None
    assert out.analysis.explanation_tamil is None


def test_other_crop_response_is_unchanged() -> None:
    out = NutrientReportOut.from_report(_report(crop="Paddy"))
    assert out.analysis is not None
    assert out.analysis.status == "confirmed"
    assert out.analysis.confidence == 91
    assert out.analysis.confidence_band == "high"
    assert [r.category for r in out.recommendations] == ["nutrient"]


def test_groundnut_abstention_is_preserved() -> None:
    out = NutrientReportOut.from_report(
        _report(primary=None, status="not_confirmed")
    )
    assert out.analysis is not None
    assert out.analysis.status == "not_confirmed"
    assert out.analysis.result_code == "abstained"
    assert out.analysis.confidence == 91


def test_groundnut_specific_claim_is_suppressed_even_when_abstained() -> None:
    out = NutrientReportOut.from_report(
        _report(primary="nitrogen", status="not_confirmed")
    )
    assert out.analysis is not None
    assert out.analysis.status == "not_confirmed"
    assert out.analysis.result_code == "abstained"
    assert out.analysis.confidence is None
    assert out.analysis.confidence_band is None
    assert out.analysis.explanation_english is None
    assert [r.category for r in out.recommendations] == ["test", "expert"]
