from app.modules.nutrient import provider as provider_module
from app.modules.nutrient.engine import NutrientAssessment
from app.modules.nutrient.provider import MockNutrientProvider, UnavailableNutrientProvider
from app.modules.nutrient.safety import NutrientResultCode, build_safe_result


def assessment(**changes):
    values = dict(
        primary_deficiency="nitrogen",
        secondary_deficiency=None,
        status="possible",
        confidence=68,
        severity="moderate",
        affected_area="widespread",
        soil_supports=None,
        satellite_supports=False,
        weather_supports=False,
        disease_conflict=False,
        needs_test=True,
        needs_expert=False,
    )
    values.update(changes)
    return NutrientAssessment(**values)


def test_incomplete_corroboration_abstains_and_is_not_expert_verified() -> None:
    result = build_safe_result(assessment())
    assert result.code == NutrientResultCode.ABSTAINED
    assert result.expert_verified is False
    assert result.evidence_missing


def test_conflicting_disease_never_presented_as_nutrient_finding() -> None:
    result = build_safe_result(assessment(status="confirmed", confidence=90, disease_conflict=True))
    assert result.code == NutrientResultCode.ABSTAINED
    assert result.primary_finding is None
    assert "differential_review" in result.suggested_next_evidence


def test_supported_finding_requires_compatible_corroboration() -> None:
    result = build_safe_result(
        assessment(status="confirmed", confidence=80, soil_supports=True, needs_test=False)
    )
    assert result.code == NutrientResultCode.SUPPORTED_FINDING
    assert result.primary_finding == "nitrogen"


def test_no_response_fields_contain_pesticide_or_brand_advice() -> None:
    result = build_safe_result(assessment())
    serialized = repr(result).lower()
    assert "pesticide" not in serialized
    assert "brand" not in serialized


def test_missing_credentials_never_selects_mock_in_field_build(monkeypatch) -> None:
    monkeypatch.setattr(provider_module, "GEMINI_API_KEY", "")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("NUTRIENT_PROVIDER", "mock")
    assert isinstance(provider_module.get_default_provider(), UnavailableNutrientProvider)


def test_mock_requires_explicit_development_configuration(monkeypatch) -> None:
    monkeypatch.setattr(provider_module, "GEMINI_API_KEY", "")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("NUTRIENT_PROVIDER", "mock")
    assert isinstance(provider_module.get_default_provider(), MockNutrientProvider)
