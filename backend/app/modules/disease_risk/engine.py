from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .schemas import RulePack


class RiskOutcome(StrEnum):
    RULE_PACK_UNAVAILABLE = "RULE_PACK_UNAVAILABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    STAGE_UNCONFIRMED = "STAGE_UNCONFIRMED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    CONDITIONS_NOT_MET = "CONDITIONS_NOT_MET"
    RISK_CONDITIONS_PRESENT = "RISK_CONDITIONS_PRESENT"


@dataclass(frozen=True)
class RiskInputs:
    crop_id: str
    confirmed_stage: str | None
    stage_confirmed: bool
    weather: dict[str, float]
    weather_source: str
    weather_observed_at: datetime | None
    region: str | None
    season: str | None
    evaluated_at: datetime


@dataclass(frozen=True)
class RiskEvaluation:
    outcome: RiskOutcome
    evidence_used: dict = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    matched_conditions: list[str] = field(default_factory=list)
    rule_pack_id: str | None = None
    rule_pack_version: str | None = None
    evaluated_at: datetime | None = None


OPS = {
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
}


def evaluate_risk(pack: RulePack | None, inputs: RiskInputs) -> RiskEvaluation:
    base = {"evaluated_at": inputs.evaluated_at}
    if pack is None:
        return RiskEvaluation(RiskOutcome.RULE_PACK_UNAVAILABLE, **base)
    lineage = dict(rule_pack_id=pack.pack_id, rule_pack_version=pack.version, **base)
    if not inputs.stage_confirmed:
        return RiskEvaluation(RiskOutcome.STAGE_UNCONFIRMED, **lineage)
    if (
        inputs.crop_id != pack.crop_id
        or inputs.confirmed_stage not in pack.confirmed_stages
        or (inputs.region is not None and inputs.region not in pack.regions)
        or (inputs.season is not None and inputs.season not in pack.seasons)
    ):
        return RiskEvaluation(RiskOutcome.OUT_OF_SCOPE, **lineage)
    missing = [v for v in pack.required_weather_variables if v not in inputs.weather]
    if inputs.weather_observed_at is None:
        missing.append("weather_observed_at")
    age_hours = (
        (inputs.evaluated_at - inputs.weather_observed_at).total_seconds() / 3600
        if inputs.weather_observed_at
        else None
    )
    completeness = 1 - len(missing) / len(pack.required_weather_variables)
    source_invalid = inputs.weather_source not in {"live", "cached"} or (
        inputs.weather_source == "cached" and not pack.cached_weather_allowed
    )
    if (
        missing
        or completeness < pack.minimum_data_completeness
        or age_hours is None
        or age_hours > pack.maximum_weather_age_hours
        or source_invalid
    ):
        return RiskEvaluation(
            RiskOutcome.INSUFFICIENT_DATA,
            missing_fields=missing,
            evidence_used={"weather_source": inputs.weather_source, "weather_age_hours": age_hours},
            **lineage,
        )
    matched = [
        f"{c.variable}:{c.operator}"
        for c in pack.conditions
        if c.variable in inputs.weather and OPS[c.operator](inputs.weather[c.variable], c.value)
    ]
    return RiskEvaluation(
        RiskOutcome.RISK_CONDITIONS_PRESENT
        if len(matched) == len(pack.conditions)
        else RiskOutcome.CONDITIONS_NOT_MET,
        evidence_used={
            "crop_id": inputs.crop_id,
            "confirmed_stage": inputs.confirmed_stage,
            "weather": inputs.weather,
            "weather_source": inputs.weather_source,
            "weather_age_hours": age_hours,
        },
        matched_conditions=matched,
        **lineage,
    )
