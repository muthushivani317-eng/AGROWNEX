from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class WaterloggingDecision(StrEnum):
    OBSERVED_SURFACE_WATER = "observed_surface_water"
    CLEAR = "clear"
    POSSIBLE_WATERLOGGING = "possible_waterlogging"
    POSSIBLE_FLOOD_RISK = "possible_flood_risk"
    RAINFALL_RISK_ONLY = "rainfall_risk_only"
    REVIEW_REQUIRED = "review_required"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class WaterloggingEvidence:
    observed_at: datetime
    source: str
    scene_id: str | None
    baseline_scene_id: str | None
    coverage_pct: float | None
    evidence_present: list[str] = field(default_factory=list)
    evidence_missing: list[str] = field(default_factory=list)
    surface_water_change: str | None = None
    conflicting: bool = False
    stale: bool = False
    quality_usable: bool = False
    policy_verified: bool = False


@dataclass(frozen=True)
class WaterloggingAssessment:
    decision: WaterloggingDecision
    observed_at: datetime | None
    source: str | None
    coverage_pct: float | None
    evidence_present: list[str]
    evidence_missing: list[str]
    freshness: str
    explanation: str
    surface_water_change: str | None = None
    alert: str | None = None


def assess_waterlogging(
    evidence: WaterloggingEvidence | None,
    *,
    missing: list[str] | None = None,
    weather_context: dict[str, object] | None = None,
) -> WaterloggingAssessment:
    if evidence is None:
        # Reuse the Weather module's existing heavy-rain signal; do not introduce a
        # second rainfall threshold here.  This is context only, never satellite
        # confirmation, surface-water measurement, or a flood claim.
        if (
            weather_context
            and weather_context.get("status") in {"live", "cached"}
            and weather_context.get("heavy_rain_signal") is True
        ):
            return WaterloggingAssessment(
                decision=WaterloggingDecision.RAINFALL_RISK_ONLY,
                observed_at=None,
                source=str(weather_context.get("source") or "weather"),
                coverage_pct=None,
                evidence_present=["weather_heavy_rain_signal"],
                evidence_missing=sorted(set(missing or ["satellite_observation"])),
                freshness=str(weather_context.get("status")),
                explanation=(
                    "Weather conditions may increase waterlogging risk. "
                    "Satellite confirmation is not available."
                ),
            )
        return WaterloggingAssessment(
            decision=WaterloggingDecision.INSUFFICIENT_DATA,
            observed_at=None,
            source=None,
            coverage_pct=None,
            evidence_present=[],
            evidence_missing=missing or ["satellite_observation"],
            freshness="unknown",
            explanation=(
                "Waterlogging cannot be confirmed because required satellite "
                "evidence is unavailable."
            ),
        )
    missing_evidence = list(evidence.evidence_missing)
    if not evidence.scene_id:
        missing_evidence.append("current_scene")
    if not evidence.baseline_scene_id:
        missing_evidence.append("baseline_scene")
    if evidence.stale:
        missing_evidence.append("fresh_observation")
    if not evidence.quality_usable or evidence.coverage_pct is None:
        missing_evidence.append("usable_coverage")
    if missing_evidence:
        return WaterloggingAssessment(
            decision=WaterloggingDecision.INSUFFICIENT_DATA,
            observed_at=evidence.observed_at,
            source=evidence.source,
            coverage_pct=evidence.coverage_pct,
            evidence_present=evidence.evidence_present,
            evidence_missing=sorted(set(missing_evidence)),
            freshness="stale" if evidence.stale else "current",
            explanation="Waterlogging cannot be confirmed because required evidence is missing.",
        )
    if (
        evidence.conflicting
        or evidence.surface_water_change
        not in {
            "increase",
            "none",
        }
    ):
        return WaterloggingAssessment(
            decision=WaterloggingDecision.REVIEW_REQUIRED,
            observed_at=evidence.observed_at,
            source=evidence.source,
            coverage_pct=evidence.coverage_pct,
            evidence_present=evidence.evidence_present,
            evidence_missing=[],
            freshness="current",
            explanation=(
                "The available evidence needs expert review before waterlogging " "can be stated."
            ),
            surface_water_change=evidence.surface_water_change,
        )
    possible = evidence.surface_water_change == "increase"
    return WaterloggingAssessment(
        decision=(
            WaterloggingDecision.POSSIBLE_WATERLOGGING if possible else WaterloggingDecision.CLEAR
        ),
        observed_at=evidence.observed_at,
        source=evidence.source,
        coverage_pct=evidence.coverage_pct,
        evidence_present=evidence.evidence_present,
        evidence_missing=[],
        freshness="current",
        explanation=(
            "A possible surface-water increase was observed. Waterlogging is not confirmed."
            if possible
            else "No surface-water increase was observed in the usable comparison."
        ),
        surface_water_change=evidence.surface_water_change,
        # An unverified threshold may be shown as a cautious screening result,
        # but must never create an operational farmer alert.
        alert="possible_waterlogging" if possible and evidence.policy_verified else None,
    )
