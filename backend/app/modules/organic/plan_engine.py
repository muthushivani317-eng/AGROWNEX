from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.modules.action_verification.source_adapter import SourceAction
from app.modules.disease.models import DiseaseReport
from app.modules.farms.models import Farm
from app.modules.organic.governance import input_hash_is_valid
from app.modules.organic.models import OrganicInput
from app.modules.soil.models import SoilIndicatorEvidence, SoilProfile


def _code(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _source_identity(parent_id: uuid.UUID, *parts: object) -> str:
    digest = hashlib.sha256(":".join(str(part) for part in parts).encode()).hexdigest()[:24]
    return f"{parent_id}:{digest}"


def _governed(item: OrganicInput, today) -> bool:
    return bool(
        item.review_status == "approved"
        and item.reviewed_at is not None
        and (item.effective_from is None or item.effective_from <= today)
        and (item.review_due_on is None or item.review_due_on >= today)
        and input_hash_is_valid(item)
    )


@dataclass(frozen=True)
class PlanStep:
    order: int
    kind: str
    title_code: str
    requires_expert: bool
    organic_input: OrganicInput | None
    source_action: SourceAction


@dataclass(frozen=True)
class DiseasePlan:
    report_id: uuid.UUID
    support_level: str
    treatments_available: bool
    steps: list[PlanStep]


def diagnosis_is_supported(report: DiseaseReport) -> bool:
    if not report.disease or report.confidence is None or report.confidence < 70:
        return False
    reviewed = report.review_status in {"confirmed", "corrected"}
    return reviewed or report.verification_level == "verified_by_local_model"


def build_disease_plan(
    report: DiseaseReport, approved_inputs: list[OrganicInput], *, now: datetime | None = None
) -> DiseasePlan:
    generated_at = now or datetime.now(UTC)
    supported = diagnosis_is_supported(report)
    steps: list[PlanStep] = []

    def add(kind: str, title_code: str, order: int, *, item: OrganicInput | None = None):
        version = item.source_version if item else "diagnosis-safety-v1"
        steps.append(
            PlanStep(
                order=order,
                kind=kind,
                title_code=title_code,
                requires_expert=kind == "expert_confirmation",
                organic_input=item,
                source_action=SourceAction(
                    source_feature="organic_disease_plan",
                    source_record_id=_source_identity(
                        report.id, order, title_code, item.slug if item else kind
                    ),
                    source_version=version,
                    action_code=(f"organic_input.{item.slug}" if item else title_code),
                    suggestion_time=generated_at,
                    source_verified=item is not None,
                    crop_cycle_id=str(report.crop_session_id) if report.crop_session_id else None,
                ),
            )
        )

    add("scouting", "organic.disease.confirm_symptoms", 1)
    if not supported:
        add("expert_confirmation", "organic.disease.request_expert_review", 2)
        return DiseasePlan(report.id, "insufficient_diagnosis_support", False, steps)

    disease_code = _code(report.corrected_label or report.disease or "")
    crop_code = _code(report.crop or "")
    matching: list[OrganicInput] = []
    for item in approved_inputs:
        if not _governed(item, generated_at.date()):
            continue
        target_diseases = {_code(str(v)) for v in item.guidance.get("target_diseases", [])}
        crops = {_code(str(v)) for v in item.applicable_crops}
        if disease_code in target_diseases and (not crops or crop_code in crops):
            matching.append(item)
    for index, item in enumerate(matching, start=2):
        add("approved_treatment", "organic.disease.apply_approved_input", index, item=item)
    if not matching:
        add("expert_confirmation", "organic.disease.no_approved_treatment", 2)
    add("follow_up", "organic.disease.reinspect", len(steps) + 1)
    return DiseasePlan(report.id, "supported", bool(matching), steps)


@dataclass(frozen=True)
class SoilAmendmentOption:
    organic_input: OrganicInput
    rate_value: float
    rate_unit: str
    calculated_quantity: float | None
    calculated_unit: str | None
    source_action: SourceAction


@dataclass(frozen=True)
class SoilOrganicMatterPlan:
    farm_id: uuid.UUID
    area_hectares: float | None
    organic_carbon: float | None
    organic_carbon_evidence_type: str
    is_estimate: bool
    organic_carbon_trend: str | None
    organic_carbon_change: float | None
    trend_is_causal: bool
    retest_on: date | None
    options: list[SoilAmendmentOption]


def convert_area(value: float, from_unit: str, to_unit: str) -> float:
    """Convert supported farm-area units with deterministic six-decimal output."""
    factors = {"hectare": 1.0, "acre": 0.40468564224}
    if from_unit not in factors or to_unit not in factors:
        raise ValueError("UNSUPPORTED_AREA_UNIT")
    return round(float(value) * factors[from_unit] / factors[to_unit], 6)


def convert_mass(value: float, from_unit: str, to_unit: str) -> float:
    """Convert supported amendment mass units."""
    factors = {"kg": 1.0, "tonne": 1000.0}
    if from_unit not in factors or to_unit not in factors:
        raise ValueError("UNSUPPORTED_MASS_UNIT")
    return round(float(value) * factors[from_unit] / factors[to_unit], 6)


def build_soil_plan(
    farm: Farm,
    profile: SoilProfile | None,
    evidence: list[SoilIndicatorEvidence],
    approved_inputs: list[OrganicInput],
    *,
    now: datetime | None = None,
) -> SoilOrganicMatterPlan:
    generated_at = now or datetime.now(UTC)
    carbon_rows = [row for row in evidence if row.indicator == "organic_carbon"]
    carbon_rows.sort(key=lambda row: row.collected_at, reverse=True)
    selected = carbon_rows[0] if carbon_rows else None
    value = selected.numeric_value if selected else (profile.organic_carbon if profile else None)
    evidence_type = (
        selected.evidence_type if selected else (profile.source if profile else "unavailable")
    )
    estimated_types = {"AI_ESTIMATED", "RISK_INFERRED", "estimate", "satellite"}
    is_estimate = evidence_type in estimated_types
    verified_lab = [
        row
        for row in carbon_rows
        if row.evidence_type == "LAB_MEASURED" and row.verification_state == "verified"
    ]
    carbon_change = None
    carbon_trend = None
    retest_on = None
    if verified_lab:
        latest = verified_lab[0]
        retest_on = date(
            latest.collected_at.year + (latest.collected_at.month + 5) // 12,
            (latest.collected_at.month + 5) % 12 + 1,
            latest.collected_at.day,
        )
    if len(verified_lab) >= 2:
        carbon_change = round(verified_lab[0].numeric_value - verified_lab[1].numeric_value, 4)
        carbon_trend = (
            "improving" if carbon_change > 0 else "declining" if carbon_change < 0 else "stable"
        )
    options: list[SoilAmendmentOption] = []
    crop = _code(farm.crop or "")
    for item in approved_inputs:
        if not _governed(item, generated_at.date()):
            continue
        if item.category not in {"compost", "farmyard_manure", "vermicompost", "green_manure"}:
            continue
        crops = {_code(str(v)) for v in item.applicable_crops}
        if crops and crop not in crops:
            continue
        rate = item.guidance.get("application_rate")
        if not isinstance(rate, dict):
            continue
        rate_value = rate.get("value")
        rate_unit = rate.get("unit")
        if not isinstance(rate_value, int | float) or rate_value <= 0:
            continue
        if rate_unit not in {"kg/ha", "tonne/ha"}:
            continue
        calculated = float(rate_value) * farm.area_hectares if farm.area_hectares else None
        options.append(
            SoilAmendmentOption(
                organic_input=item,
                rate_value=float(rate_value),
                rate_unit=rate_unit,
                calculated_quantity=round(calculated, 3) if calculated is not None else None,
                calculated_unit=rate_unit.removesuffix("/ha") if calculated is not None else None,
                source_action=SourceAction(
                    source_feature="organic_soil_plan",
                    source_record_id=_source_identity(farm.id, item.slug),
                    source_version=item.source_version,
                    action_code=f"organic_input.{item.slug}",
                    suggestion_time=generated_at,
                    source_verified=True,
                ),
            )
        )
    return SoilOrganicMatterPlan(
        farm_id=farm.id,
        area_hectares=farm.area_hectares,
        organic_carbon=value,
        organic_carbon_evidence_type=evidence_type,
        is_estimate=is_estimate,
        organic_carbon_trend=carbon_trend,
        organic_carbon_change=carbon_change,
        trend_is_causal=False,
        retest_on=retest_on,
        options=options,
    )
