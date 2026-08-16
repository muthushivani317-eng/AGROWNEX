from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

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
    elif assessment.status == "possible" and corroborated:
        code = NutrientResultCode.POSSIBLE_FINDING
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
