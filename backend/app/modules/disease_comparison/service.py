from __future__ import annotations

import hashlib
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.modules.ai.usage_ledger import record_usage_durable

from .models import DiseaseModelComparison
from .provider import OpenAIComparisonError, OpenAIDiseaseComparisonProvider
from .schemas import DiagnosticDecision, OpenAISecondOpinion

logger = get_logger("disease_comparison.service")


def labels_agree(local_label: str | None, provider_label: str | None) -> bool | None:
    if not local_label or not provider_label:
        return None

    def normalize(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    return normalize(local_label) == normalize(provider_label)


def decide_comparison(
    *, local_status: str, local_label: str | None, opinion: OpenAISecondOpinion
) -> DiagnosticDecision:
    """Combine qualitative evidence without averaging independent confidence values."""
    unsupported = {
        "abiotic_stress",
        "nutrient_related",
        "pest_damage",
        "physical_injury",
        "unsupported_disease",
    }
    if opinion.outcome_category in unsupported or opinion.known_class_match == "low":
        return DiagnosticDecision(
            status="unsupported_or_unknown_disease",
            expert_review_required=True,
            reason_code="KNOWN_CLASS_NOT_SUPPORTED_BY_VISIBLE_EVIDENCE",
        )
    if (
        not opinion.image_usable
        or opinion.outcome_category == "insufficient_evidence"
        or opinion.assessment_status == "not_assessable"
    ):
        return DiagnosticDecision(
            status="insufficient_evidence",
            additional_photo_required=True,
            requested_photo_view=opinion.requested_photo_view,
            expert_review_required=opinion.expert_review_required,
            reason_code="VISIBLE_EVIDENCE_INSUFFICIENT",
        )
    agreement = labels_agree(local_label, opinion.possible_disease_label)
    if (
        local_status == "accepted"
        and agreement is True
        and opinion.outcome_category == "known_disease"
        and opinion.known_class_match in {"high", "medium"}
        and not opinion.additional_photo_required
    ):
        return DiagnosticDecision(
            status="strong_agreement",
            likely_disease_label=local_label,
            expert_review_required=opinion.expert_review_required,
            reason_code="LOCAL_AND_VISIBLE_EVIDENCE_AGREE",
        )
    if agreement is False or opinion.additional_photo_required:
        return DiagnosticDecision(
            status="conflict_needs_more_evidence",
            additional_photo_required=True,
            requested_photo_view=opinion.requested_photo_view,
            expert_review_required=opinion.expert_review_required,
            reason_code="LOCAL_AND_VISIBLE_EVIDENCE_CONFLICT",
        )
    return DiagnosticDecision(
        status="expert_review_required",
        expert_review_required=True,
        reason_code="NO_SAFE_AUTOMATED_CONCLUSION",
    )


async def run_shadow_comparison(
    *,
    user_id: uuid.UUID,
    image: bytes,
    content_type: str,
    crop: str,
    local_model: str,
    local_status: str,
    local_label: str | None,
    local_confidence: float | None,
) -> None:
    """Run after the farmer response; every failure is contained and recorded."""
    if not settings.openai_disease_comparison_enabled:
        return
    started = time.perf_counter()
    values: dict = {
        "provider_model": settings.openai_disease_comparison_model or "unconfigured",
        "provider_status": "unavailable",
        "error_code": None,
        "provider_label": None,
        "crop_assessment": None,
        "assessment_status": None,
        "alternative_labels": [],
        "visual_observations": [],
        "agrees_with_local": None,
        "latency_ms": None,
        "input_tokens": None,
        "output_tokens": None,
    }
    try:
        result = await OpenAIDiseaseComparisonProvider().compare(
            image=image, content_type=content_type, crop=crop
        )
        opinion = result.opinion
        values.update(
            provider_model=result.model,
            provider_status="completed",
            provider_label=opinion.possible_disease_label,
            crop_assessment=opinion.crop_assessment,
            assessment_status=opinion.assessment_status,
            alternative_labels=[item.disease for item in opinion.differential_diagnoses],
            visual_observations=opinion.observed_symptoms,
            agrees_with_local=labels_agree(local_label, opinion.possible_disease_label),
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        await record_usage_durable(
            farmer_id=user_id,
            module="disease_comparison",
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
            provider="openai",
        )
    except OpenAIComparisonError as exc:
        values["error_code"] = str(exc)
        values["latency_ms"] = round((time.perf_counter() - started) * 1000)
    except Exception:
        values["error_code"] = "OPENAI_COMPARISON_UNEXPECTED_FAILURE"
        values["latency_ms"] = round((time.perf_counter() - started) * 1000)
        logger.exception("OpenAI shadow comparison failed")

    try:
        async with SessionLocal() as session:
            session.add(
                DiseaseModelComparison(
                    user_id=user_id,
                    image_sha256=hashlib.sha256(image).hexdigest(),
                    crop=crop,
                    local_model=local_model,
                    local_status=local_status,
                    local_label=local_label,
                    local_confidence=local_confidence,
                    provider="openai",
                    test_mode=True,
                    exposed_to_farmer=False,
                    **values,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("OpenAI shadow comparison record persistence failed")


async def list_comparisons(session: AsyncSession, *, limit: int = 100):
    from sqlalchemy import select

    result = await session.execute(
        select(DiseaseModelComparison)
        .order_by(DiseaseModelComparison.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
