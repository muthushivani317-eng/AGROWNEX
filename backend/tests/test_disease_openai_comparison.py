from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import settings
from app.modules.auth.models import User
from app.modules.disease_comparison.models import DiseaseModelComparison
from app.modules.disease_comparison.provider import (
    SYSTEM_PROMPT,
    ImageEvidence,
    OpenAIDiseaseComparisonProvider,
    ProviderResult,
)
from app.modules.disease_comparison.schemas import OpenAISecondOpinion
from app.modules.disease_comparison.service import (
    decide_comparison,
    labels_agree,
    run_shadow_comparison,
)
from pydantic import ValidationError
from sqlalchemy import select


def opinion(label: str | None = "sigatoka_leaf_spot") -> OpenAISecondOpinion:
    return OpenAISecondOpinion(
        crop_assessment="consistent",
        assessment_status="possible",
        image_usable=True,
        outcome_category="known_disease",
        known_class_match="high",
        possible_disease_label=label,
        differential_diagnoses=[],
        observed_symptoms=["Dark leaf lesions are visible"],
        evidence_supporting=["Leaf lesion pattern"],
        evidence_missing=[],
        additional_photo_required=False,
        requested_photo_view=None,
        expert_review_required=False,
    )


def test_shadow_schema_forbids_treatment_content_fields():
    with pytest.raises(ValidationError):
        OpenAISecondOpinion.model_validate(
            {
                **opinion().model_dump(),
                "treatment": "Apply an unsupported chemical",
            }
        )


def test_prompt_is_observations_first_and_forbids_guessing_or_treatment():
    assert "observable evidence" in SYSTEM_PROMPT
    assert "Do not select a disease" in SYSTEM_PROMPT
    assert "unsupported_disease" in SYSTEM_PROMPT
    assert "pesticide" in SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_provider_sends_bounded_labelled_multi_image_evidence(monkeypatch):
    monkeypatch.setattr(settings, "openai_disease_comparison_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_disease_comparison_model", "test-vision-model")
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = lambda: None
    response.json.return_value = {
        "model": "test-vision-model",
        "output_text": opinion().model_dump_json(),
        "usage": {},
    }
    post = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "app.modules.disease_comparison.provider.get_http_client",
        lambda: type("Client", (), {"post": post})(),
    )

    await OpenAIDiseaseComparisonProvider().compare_images(
        images=[
            ImageEvidence(view="whole_plant", image=b"a", content_type="image/jpeg"),
            ImageEvidence(view="affected_leaf", image=b"b", content_type="image/jpeg"),
        ],
        crop="banana",
    )

    body = post.await_args.kwargs["json"]
    content = body["input"][0]["content"]
    assert len([item for item in content if item["type"] == "input_image"]) == 2
    assert "whole_plant" in content[1]["text"]


def test_label_agreement_is_conservative():
    assert labels_agree("Sigatoka leaf spot", "sigatoka_leaf_spot") is True
    assert labels_agree("cordana_leaf_spot", "sigatoka_leaf_spot") is False
    assert labels_agree(None, "sigatoka_leaf_spot") is None


def test_strong_agreement_uses_qualitative_status_and_never_averages_scores():
    decision = decide_comparison(
        local_status="accepted",
        local_label="sigatoka_leaf_spot",
        opinion=opinion(),
    )
    assert decision.status == "strong_agreement"
    assert decision.likely_disease_label == "sigatoka_leaf_spot"
    assert decision.additional_photo_required is False
    assert not hasattr(decision, "combined_confidence")


def test_conflict_requests_the_specific_missing_view_without_choosing_a_winner():
    second = opinion("cordana_leaf_spot").model_copy(
        update={
            "evidence_missing": ["Leaf underside is not visible"],
            "additional_photo_required": True,
            "requested_photo_view": "leaf_underside",
        }
    )
    decision = decide_comparison(
        local_status="accepted",
        local_label="sigatoka_leaf_spot",
        opinion=second,
    )
    assert decision.status == "conflict_needs_more_evidence"
    assert decision.likely_disease_label is None
    assert decision.requested_photo_view == "leaf_underside"


@pytest.mark.parametrize(
    "category",
    ["abiotic_stress", "nutrient_related", "pest_damage", "physical_injury", "unsupported_disease"],
)
def test_unsupported_outcomes_never_force_a_known_disease(category):
    second = opinion(None).model_copy(
        update={
            "outcome_category": category,
            "known_class_match": "low",
            "expert_review_required": True,
        }
    )
    decision = decide_comparison(
        local_status="accepted",
        local_label="sigatoka_leaf_spot",
        opinion=second,
    )
    assert decision.status == "unsupported_or_unknown_disease"
    assert decision.likely_disease_label is None
    assert decision.expert_review_required is True


@pytest.mark.asyncio
async def test_disabled_shadow_mode_makes_no_provider_call(monkeypatch):
    compare = AsyncMock()
    monkeypatch.setattr(settings, "openai_disease_comparison_enabled", False)
    monkeypatch.setattr(
        "app.modules.disease_comparison.service.OpenAIDiseaseComparisonProvider.compare",
        compare,
    )
    await run_shadow_comparison(
        user_id=uuid.uuid4(),
        image=b"image",
        content_type="image/jpeg",
        crop="banana",
        local_model="banana-v3",
        local_status="accepted",
        local_label="sigatoka_leaf_spot",
        local_confidence=0.9,
    )
    compare.assert_not_awaited()


@pytest.mark.asyncio
async def test_completed_shadow_result_is_stored_but_never_exposed(
    db_session, session_factory, monkeypatch
):
    user = User(firebase_uid=f"openai-shadow-{uuid.uuid4()}", status="active")
    db_session.add(user)
    await db_session.flush()
    monkeypatch.setattr(settings, "openai_disease_comparison_enabled", True)
    monkeypatch.setattr(settings, "openai_disease_comparison_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_disease_comparison_model", "test-vision-model")
    monkeypatch.setattr("app.modules.disease_comparison.service.SessionLocal", session_factory)
    monkeypatch.setattr("app.modules.disease_comparison.service.record_usage_durable", AsyncMock())
    monkeypatch.setattr(
        "app.modules.disease_comparison.service.OpenAIDiseaseComparisonProvider.compare",
        AsyncMock(
            return_value=ProviderResult(
                opinion=opinion(),
                model="test-vision-model",
                latency_ms=12,
                input_tokens=100,
                output_tokens=20,
            )
        ),
    )

    await run_shadow_comparison(
        user_id=user.id,
        image=b"private-image-bytes",
        content_type="image/jpeg",
        crop="banana",
        local_model="banana-v3",
        local_status="accepted",
        local_label="sigatoka_leaf_spot",
        local_confidence=0.91,
    )

    row = (await db_session.execute(select(DiseaseModelComparison))).scalar_one()
    assert row.provider_status == "completed"
    assert row.agrees_with_local is True
    assert row.test_mode is True
    assert row.exposed_to_farmer is False
    assert row.image_sha256 and "private-image-bytes" not in row.image_sha256
