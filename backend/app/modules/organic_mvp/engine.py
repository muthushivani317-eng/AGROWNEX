"""Fail-closed rules for the organic pilot; no app-generated certification."""
from __future__ import annotations

from datetime import date, timedelta

from app.core.exceptions import ValidationError

TRIAL_NOTICE = "Pre-certification trial—not PGS certified."
PGS_STATES = frozenset({
    "pre_certification_trial", "pgs_eligibility_review",
    "regional_council_approval_required", "pgs_registration_pending",
    "pgs_green_under_conversion", "pgs_organic", "non_compliance_review",
})

# Organic Readiness Check pathway codes. The original three are deliberately
# soft/non-committal (never claims conversion readiness outright). The
# blueprint's four (2026-09-23, owner-approved) make a stronger claim, so
# they're additive, not a replacement -- an admin still has to author and
# approve a rules version using them before any farmer sees a result, same
# review gate as every other pathway here.
READINESS_PATHWAYS = frozenset({
    "learning", "pre_certification_trial", "eligibility_review",
    "ready_full_conversion", "start_one_plot", "begin_soil_restoration", "not_ready",
})


def score_readiness(answers: dict, rules: dict) -> dict:
    """Score only a reviewed, versioned question set; reject incomplete answers."""
    questions = rules.get("questions") or []
    if not questions:
        raise ValidationError("No approved readiness questions are available.")
    total = 0
    maximum = 0
    flags: list[str] = []
    for question in questions:
        key = question["id"]
        choices = question["options"]
        if key not in answers or answers[key] not in choices:
            raise ValidationError(f"A valid answer is required for {key}.")
        choice = choices[answers[key]]
        total += choice["points"]
        maximum += max(option["points"] for option in choices.values())
        if choice.get("risk_flag"):
            flags.append(choice["risk_flag"])
    score = round(total * 100 / maximum) if maximum else 0
    bands = rules.get("bands") or []
    match = next((band for band in bands if band["min"] <= score <= band["max"]), None)
    if match is None:
        raise ValidationError("Readiness scoring rules are incomplete.")
    return {
        "score": score,
        "pathway": match["pathway"],
        "recommendation_ta": match["recommendation_ta"],
        "recommendation_en": match.get("recommendation_en"),
        "risk_flags": flags,
    }


def validate_pgs_transition(*, requested: str, partial_conversion: bool,
                            council_approval_ref: str | None,
                            certificate_id: str | None, issuing_authority: str | None,
                            valid_from: date | None, valid_to: date | None,
                            verified: bool, major_non_compliance: bool) -> None:
    if requested not in PGS_STATES:
        raise ValidationError("Unknown PGS state.")
    if partial_conversion and not council_approval_ref and requested != "regional_council_approval_required":
        raise ValidationError("Regional Council approval required.")
    if requested in {"pgs_green_under_conversion", "pgs_organic"}:
        if not (verified and certificate_id and issuing_authority and valid_from and valid_to):
            raise ValidationError("Verified certificate, authority and validity dates are required.")
        if not valid_from <= date.today() <= valid_to:
            raise ValidationError("Certification evidence is not currently valid.")
        if major_non_compliance:
            raise ValidationError("Non-compliance review required before verified status.")
    if requested == "pgs_organic" and partial_conversion and not council_approval_ref:
        raise ValidationError("Regional Council approval required.")


def schedule_reviewed_tasks(tasks: list[dict], sowing_date: date) -> list[dict]:
    if not sowing_date:
        raise ValidationError("Sowing date is required to schedule a crop plan.")
    result = []
    for task in tasks:
        day = task.get("day_offset")
        if not isinstance(day, int) or not 0 <= day <= 90:
            raise ValidationError("Task day must be within the 90-day plan.")
        if not task.get("title_ta") or not task.get("body_ta"):
            raise ValidationError("Reviewed tasks require Tamil title and instructions.")
        result.append({**task, "due_on": sowing_date + timedelta(days=day)})
    return result


def forecast_gate(rows: list[dict]) -> str | None:
    """Forecasts must come only from real enrolled production farms."""
    if not rows:
        return "No farmers enrolled"
    if any(row.get("is_test") for row in rows):
        return "Insufficient data for harvest forecast"
    required = ("farm_id", "area_hectares", "crop_id", "sowing_date", "expected_harvest_start", "expected_harvest_end")
    if any(any(not row.get(key) for key in required) or row["area_hectares"] <= 0 for row in rows):
        return "Insufficient data for harvest forecast"
    return None
