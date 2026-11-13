"""Nutrient request/response schemas (docs: reuse response envelope).

Deficiencies, symptoms and recommendations travel as localization ``code``s /
enum values so the Tamil-first client renders them. An unconfirmed or unavailable
value is ``null`` / ``not_confirmed`` and surfaced honestly — never fabricated.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.nutrient.crops import is_groundnut_nutrient_crop
from app.modules.nutrient.engine import NutrientAssessment, SoilReference, soil_signal
from app.modules.nutrient.models import (
    NutrientHistory,
    NutrientRecommendation,
    NutrientReport,
)
from app.modules.nutrient.safety import build_safe_result

_MIME_PATTERN = "^image/(jpeg|png|webp)$"


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class AnalyzeNutrientRequest(BaseModel):
    image_base64: str = Field(min_length=16, max_length=24_000_000)
    mime_type: str = Field(pattern=_MIME_PATTERN)
    farm_id: uuid.UUID
    crop: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, pattern="^(ta|en)$")
    capture_method: str | None = Field(default=None, pattern="^(camera|gallery)$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
class NutrientRecommendationOut(BaseModel):
    category: str
    code: str
    nutrient: str | None
    severity: str
    priority: str

    @classmethod
    def from_model(cls, rec: NutrientRecommendation) -> NutrientRecommendationOut:
        return cls(
            category=rec.category,
            code=rec.code,
            nutrient=rec.nutrient,
            severity=rec.severity,
            priority=rec.priority,
        )


class NutrientAnalysisOut(BaseModel):
    primary_deficiency: str | None
    secondary_deficiency: str | None
    status: str
    confidence: int | None
    severity: str
    affected_area: str | None
    disease_conflict: bool
    needs_test: bool
    needs_expert: bool
    soil_reference: dict | None
    satellite_reference: dict | None
    weather_reference: dict | None
    explanation_tamil: str | None
    explanation_english: str | None
    result_code: str
    confidence_band: str | None
    evidence_observed: list[str]
    evidence_missing: list[str]
    conflicts: list[str]
    abstention_reason: str | None
    suggested_next_evidence: list[str]
    expert_verified: bool


def _groundnut_required_recommendations() -> list[NutrientRecommendationOut]:
    """Only evidence/review actions are safe for a Groundnut-specific finding."""
    return [
        NutrientRecommendationOut(
            category="test", code="nutrient.rec.test.soil_test", nutrient=None,
            severity="warning", priority="medium",
        ),
        NutrientRecommendationOut(
            category="expert", code="nutrient.rec.expert.consult", nutrient=None,
            severity="warning", priority="medium",
        ),
    ]


class NutrientReportOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    crop: str | None
    image_url: str
    thumbnail_url: str | None
    capture_date: date | None
    provider: str
    model_used: str | None
    status: str
    language: str
    latitude: float | None
    longitude: float | None
    weather_snapshot: dict | None
    analysis: NutrientAnalysisOut | None
    symptoms: list[str]
    recommendations: list[NutrientRecommendationOut]
    created_at: datetime

    @classmethod
    def from_report(cls, report: NutrientReport) -> NutrientReportOut:
        analysis = None
        groundnut_specific_claim = False
        groundnut_specific_finding = False
        if report.analysis is not None:
            a = report.analysis
            soil = a.soil_reference or {}
            # Rebuild the same SoilReference the engine used at analysis time and
            # reuse its own soil_signal() rather than re-deriving soil_supports here
            # -- this used to only check macro_ratings (N/P/K), so a soil-confirmed
            # micronutrient deficiency (zinc/iron/boron/copper/manganese, tracked via
            # deficient_micronutrients, not macro_ratings) always came back as
            # unsupported and got abstained on the API even though it was genuinely
            # soil-confirmed when the report was created (2026-08 pre-release audit).
            soil_ref = SoilReference(
                has_data=bool(soil.get("has_data", False)),
                macro_ratings=soil.get("macro_ratings") or {},
                deficient_micronutrients=tuple(soil.get("deficient_micronutrients") or []),
            )
            _, soil_supports = (
                soil_signal(a.primary_deficiency, soil_ref)
                if a.primary_deficiency
                else (0, None)
            )
            safe = build_safe_result(
                NutrientAssessment(
                    primary_deficiency=a.primary_deficiency,
                    secondary_deficiency=a.secondary_deficiency,
                    status=a.status,
                    confidence=a.confidence,
                    severity=a.severity,
                    affected_area=a.affected_area,
                    soil_supports=soil_supports,
                    satellite_supports=False,
                    weather_supports=False,
                    disease_conflict=a.disease_conflict,
                    needs_test=a.needs_test,
                    needs_expert=a.needs_expert,
                )
            )
            groundnut_specific_claim = bool(
                is_groundnut_nutrient_crop(report.crop) and a.primary_deficiency
            )
            groundnut_specific_finding = bool(
                groundnut_specific_claim and safe.code.value != "abstained"
            )
            analysis = NutrientAnalysisOut(
                primary_deficiency=a.primary_deficiency,
                secondary_deficiency=a.secondary_deficiency,
                status="possible" if groundnut_specific_finding else a.status,
                # Groundnut has no validated nutrient-specific calibration.
                confidence=None if groundnut_specific_claim else a.confidence,
                severity=a.severity,
                affected_area=a.affected_area,
                disease_conflict=a.disease_conflict,
                needs_test=True if groundnut_specific_claim else a.needs_test,
                needs_expert=True if groundnut_specific_claim else a.needs_expert,
                soil_reference=a.soil_reference,
                satellite_reference=a.satellite_reference,
                weather_reference=a.weather_reference,
                explanation_tamil=None if groundnut_specific_claim else a.explanation_tamil,
                explanation_english=None if groundnut_specific_claim else a.explanation_english,
                result_code="possible_finding" if groundnut_specific_finding else safe.code.value,
                confidence_band=None if groundnut_specific_claim else safe.confidence_band,
                evidence_observed=safe.evidence_observed,
                evidence_missing=safe.evidence_missing,
                conflicts=safe.conflicts,
                abstention_reason=safe.abstention_reason,
                suggested_next_evidence=(
                    ["soil_or_tissue_test", "expert_review"]
                    if groundnut_specific_claim
                    else safe.suggested_next_evidence
                ),
                expert_verified=False,
            )
        return cls(
            id=report.id,
            farm_id=report.farm_id,
            crop=report.crop,
            image_url=report.image_url,
            thumbnail_url=report.thumbnail_url,
            capture_date=report.capture_date,
            provider=report.provider,
            model_used=report.model_used,
            status=report.status,
            language=report.language,
            latitude=report.latitude,
            longitude=report.longitude,
            weather_snapshot=report.weather_snapshot,
            analysis=analysis,
            symptoms=[s.code for s in report.symptoms],
            recommendations=(
                _groundnut_required_recommendations()
                if groundnut_specific_claim
                else [NutrientRecommendationOut.from_model(r) for r in report.recommendations]
            ),
            created_at=report.created_at,
        )


class NutrientReportSummaryOut(BaseModel):
    """A compact history row — status + primary deficiency + confidence."""

    id: uuid.UUID
    farm_id: uuid.UUID
    crop: str | None
    primary_deficiency: str | None
    status: str
    confidence: int
    severity: str | None
    recorded_at: datetime

    @classmethod
    def from_history(cls, h: NutrientHistory) -> NutrientReportSummaryOut:
        return cls(
            id=h.report_id or h.id,
            farm_id=h.farm_id,
            crop=h.crop,
            primary_deficiency=h.primary_deficiency,
            status=h.status,
            confidence=h.confidence,
            severity=h.severity,
            recorded_at=h.recorded_at,
        )


class NutrientHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farm_id: uuid.UUID
    report_id: uuid.UUID | None
    crop: str | None
    primary_deficiency: str | None
    status: str
    confidence: int
    severity: str | None
    recorded_at: datetime
