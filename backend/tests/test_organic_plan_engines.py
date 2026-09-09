from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.modules.disease.models import DiseaseReport
from app.modules.farms.models import Farm
from app.modules.organic.governance import canonical_input_hash
from app.modules.organic.models import OrganicInput
from app.modules.organic.plan_engine import build_disease_plan, build_soil_plan
from app.modules.organic.schemas import DiseaseOrganicPlanOut, SoilOrganicMatterPlanOut
from app.modules.soil.models import SoilIndicatorEvidence, SoilProfile


def _input(*, target: str = "leaf_spot", rate: dict | None = None) -> OrganicInput:
    item = OrganicInput(
        id=uuid.uuid4(),
        slug="tnau-approved-compost",
        category="compost",
        name_en="Approved compost",
        name_ta="அங்கீகரிக்கப்பட்ட உரம்",
        purpose_en="Source-reviewed use",
        purpose_ta="ஆதார மதிப்பாய்வு பயன்பாடு",
        guidance={
            "target_diseases": [target],
            **({"application_rate": rate} if rate else {}),
        },
        applicable_crops=["paddy"],
        applicable_stages=[],
        applicable_regions=["Tamil Nadu"],
        limitations={},
        source_organization="TNAU",
        document_reference="TNAU guide",
        source_url="https://example.invalid/tnau",
        source_version="2026.1",
        content_hash="pending",
        review_status="approved",
        reviewed_at=datetime.now(UTC),
    )
    item.content_hash = canonical_input_hash(item)
    return item


def test_weak_diagnosis_never_emits_treatment():
    report = DiseaseReport(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        disease="Leaf spot",
        crop="paddy",
        confidence=96,
        raw_response={"local_model": {"label": None, "agreement": False}},
    )
    plan = build_disease_plan(report, [_input()])
    assert plan.support_level == "insufficient_diagnosis_support"
    assert not plan.treatments_available
    assert [step.kind for step in plan.steps] == ["scouting", "expert_confirmation"]


def test_supported_diagnosis_uses_only_matching_approved_input():
    report = DiseaseReport(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        disease="Leaf spot",
        crop="paddy",
        confidence=82,
        raw_response={"local_model": {"label": "leaf_spot", "agreement": True}},
    )
    plan = build_disease_plan(report, [_input(), _input(target="blast")])
    treatment = [step for step in plan.steps if step.kind == "approved_treatment"]
    assert len(treatment) == 1
    assert treatment[0].source_action.source_verified is True
    assert treatment[0].source_action.source_version == "2026.1"
    assert DiseaseOrganicPlanOut.model_validate(plan).steps[1].organic_input is not None


def test_soil_plan_preserves_unknowns_without_area_or_measurement():
    farm = Farm(id=uuid.uuid4(), user_id=uuid.uuid4(), name="Unknown", crop="paddy")
    plan = build_soil_plan(
        farm,
        None,
        [],
        [_input(rate={"value": 2, "unit": "tonne/ha"})],
    )
    assert plan.organic_carbon is None
    assert plan.organic_carbon_evidence_type == "unavailable"
    assert plan.area_hectares is None
    assert plan.options[0].calculated_quantity is None


def test_soil_quantity_is_deterministic_and_estimate_is_labelled():
    user_id = uuid.uuid4()
    farm_id = uuid.uuid4()
    farm = Farm(id=farm_id, user_id=user_id, name="Measured", crop="paddy", area_hectares=2.5)
    profile = SoilProfile(
        user_id=user_id,
        farm_id=farm_id,
        organic_carbon=0.42,
        source="lab",
        confidence=95,
    )
    evidence = SoilIndicatorEvidence(
        user_id=user_id,
        farm_id=farm_id,
        indicator="organic_carbon",
        numeric_value=0.39,
        unit="%",
        evidence_type="AI_ESTIMATED",
        collection_method="remote",
        collected_at=date.today(),
        source_reference="scene-1",
        spatial_coverage="farm",
        verification_state="unverified",
    )
    plan = build_soil_plan(
        farm,
        profile,
        [evidence],
        [_input(rate={"value": 2.0, "unit": "tonne/ha"})],
    )
    assert plan.organic_carbon == 0.39
    assert plan.is_estimate is True
    assert plan.options[0].calculated_quantity == 5.0
    assert plan.options[0].calculated_unit == "tonne"
    assert SoilOrganicMatterPlanOut.model_validate(plan).options[0].rate_unit == "tonne/ha"


def test_soil_plan_rejects_unrecognized_rate_units():
    farm = Farm(id=uuid.uuid4(), user_id=uuid.uuid4(), name="Units", crop="paddy", area_hectares=2)
    plan = build_soil_plan(
        farm,
        None,
        [],
        [_input(rate={"value": 10, "unit": "bags/acre"})],
    )
    assert plan.options == []
