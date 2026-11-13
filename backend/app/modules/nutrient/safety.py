from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.modules.nutrient.crops import is_groundnut_nutrient_crop
from app.modules.nutrient.engine import NutrientAssessment


class NutrientResultCode(StrEnum):
    SUPPORTED_FINDING = "supported_finding"
    POSSIBLE_FINDING = "possible_finding"
    ABSTAINED = "abstained"
    INVALID_IMAGE = "invalid_image"
    CROP_MISMATCH = "crop_mismatch"
    UNSUPPORTED_CROP = "unsupported_crop"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


@dataclass(frozen=True)
class SafeNutrientResult:
    code: NutrientResultCode
    primary_finding: str | None
    confidence_band: str
    evidence_observed: list[str]
    evidence_missing: list[str]
    conflicts: list[str]
    abstention_reason: str | None
    suggested_next_evidence: list[str]
    expert_verified: bool = False


@dataclass(frozen=True)
class ConsumerSafeNutrientFinding:
    """Sanitized read view; raw provider evidence remains unchanged in storage."""

    primary_deficiency: str | None
    status: str
    confidence: int | None
    needs_test: bool
    needs_expert: bool
    groundnut_specific_restricted: bool = False


def consumer_safe_nutrient_finding(
    *,
    crop: str | None,
    primary_deficiency: str | None,
    status: str,
    confidence: int | None,
    needs_test: bool,
    needs_expert: bool = False,
) -> ConsumerSafeNutrientFinding:
    """Apply crop-scoped policy whenever persisted/provider data is consumed.

    A Groundnut-specific nutrient name is audit evidence only. Downstream engines
    must not treat it as confirmed, calibrated, or automatically actionable.
    """
    restricted = bool(
        is_groundnut_nutrient_crop(crop) and primary_deficiency
    )
    if restricted:
        return ConsumerSafeNutrientFinding(
            # Downstream engines do not need the unvalidated nutrient name; keeping
            # it here could accidentally trigger nutrient-specific actions.
            primary_deficiency=None,
            status="not_confirmed",
            confidence=None,
            needs_test=True,
            needs_expert=True,
            groundnut_specific_restricted=True,
        )
    return ConsumerSafeNutrientFinding(
        primary_deficiency=primary_deficiency,
        status=status,
        confidence=confidence,
        needs_test=needs_test,
        needs_expert=needs_expert,
    )


def build_safe_result(assessment: NutrientAssessment) -> SafeNutrientResult:
    observed: list[str] = []
    missing: list[str] = []
    conflicts: list[str] = []
    if assessment.soil_supports is True:
        observed.append("compatible_soil_evidence")
    elif assessment.soil_supports is False:
        conflicts.append("soil_contradiction")
    else:
        missing.append("soil_or_tissue_evidence")
    if assessment.satellite_supports:
        observed.append("supporting_canopy_observation")
    if assessment.weather_supports:
        observed.append("supporting_weather_context")
    if assessment.disease_conflict:
        conflicts.append("disease_or_differential_ambiguity")
    band = (
        "low" if assessment.confidence < 50 else "medium" if assessment.confidence < 75 else "high"
    )
    corroborated = assessment.soil_supports is True
    # A recent disease on the farm does not hide a clear nutrient finding: the
    # farmer sees the likely deficiency and its fix, flagged as overlapping with
    # the disease and asking for an expert check (decided 2026-09-27). A soil
    # test that contradicts the finding still abstains.
    if (
        conflicts == ["disease_or_differential_ambiguity"]
        and assessment.primary_deficiency
        and assessment.status in {"confirmed", "possible"}
    ):
        return SafeNutrientResult(
            NutrientResultCode.POSSIBLE_FINDING,
            assessment.primary_deficiency,
            band,
            observed,
            missing,
            conflicts,
            None,
            ["soil_or_tissue_test", "expert_review"],
        )
    if conflicts:
        return SafeNutrientResult(
            NutrientResultCode.ABSTAINED,
            None,
            band,
            observed,
            missing,
            conflicts,
            "conflicting_evidence",
            ["differential_review", "expert_review"],
        )
    if assessment.status == "confirmed" and corroborated:
        code = NutrientResultCode.SUPPORTED_FINDING
    elif assessment.status in {"confirmed", "possible"}:
        # A clear visual finding with no contradicting evidence is shown to the
        # farmer as a *likely* deficiency (with its confidence), together with a
        # soil/tissue test to confirm it -- never as a confirmed one.
        next_evidence = ["soil_or_tissue_test"]
        if assessment.needs_expert:
            next_evidence.append("expert_review")
        return SafeNutrientResult(
            NutrientResultCode.POSSIBLE_FINDING,
            assessment.primary_deficiency,
            band,
            observed,
            missing,
            [],
            None,
            next_evidence,
        )
    else:
        return SafeNutrientResult(
            NutrientResultCode.ABSTAINED,
            None,
            band,
            observed,
            missing or ["compatible_corroboration"],
            [],
            "insufficient_compatible_evidence",
            ["soil_or_tissue_test", "expert_review"],
        )
    return SafeNutrientResult(
        code,
        assessment.primary_deficiency,
        band,
        observed,
        missing,
        [],
        None,
        ["expert_review"] if assessment.needs_expert else [],
    )
