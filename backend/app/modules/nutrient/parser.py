"""Structured validation of the vision response (pure, tested).

Parses the visual-analysis model output into a normalized ``NutrientObservation``.
It is deliberately lenient about *whether* a deficiency was seen — an empty/unknown
primary is a valid "nothing conclusive" outcome that the engine turns into an honest
``not_confirmed``. It is strict about validity: unknown nutrient names, symptom codes
and out-of-range confidence are dropped rather than trusted (never fabricated).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.modules.nutrient.constants import (
    ALL_SYMPTOMS,
    AffectedArea,
    Nutrient,
    Severity,
)

_VALID_NUTRIENTS = {n.value for n in Nutrient}
_VALID_SEVERITIES = {s.value for s in Severity}
_VALID_AREAS = {a.value for a in AffectedArea}


class ObservationParseError(ValueError):
    """Raised when the model output is not valid JSON."""


@dataclass
class NutrientObservation:
    """A normalized *visual* observation from the analysis provider (no verdict)."""

    plant_present: bool
    reject_reason: str | None
    crop: str
    visible_symptoms: list[str]
    primary: str | None
    secondary: str | None
    visual_confidence: int
    severity: str
    affected_area: str
    explanation_tamil: str
    explanation_english: str
    model_used: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ObservationParseError("no JSON object found")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ObservationParseError(str(exc)) from exc
    if not isinstance(data, dict):
        raise ObservationParseError("response is not a JSON object")
    return data


def _str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _bounded_int(value: Any) -> int | None:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 100 else None


def _nutrient(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text if text in _VALID_NUTRIENTS else None


def _symptoms(value: Any) -> list[str]:
    # Keep only recognised symptom codes, de-duplicated in order (never invented).
    seen: dict[str, None] = {}
    for item in _str_list(value):
        code = item.strip().lower()
        if code in ALL_SYMPTOMS and code not in seen:
            seen[code] = None
    return list(seen)


def parse_observation(text: str) -> NutrientObservation:
    data = _extract_json(text)
    plant_present = bool(data.get("plant_present", True))
    reject = data.get("reject_reason")
    reject_reason = str(reject).strip().lower() if reject else None
    explanation_tamil = str(data.get("explanation_tamil", "")).strip()
    explanation_english = str(data.get("explanation_english", "")).strip()

    if not plant_present:
        return NutrientObservation(
            plant_present=False,
            reject_reason=reject_reason,
            crop="unknown",
            visible_symptoms=[],
            primary=None,
            secondary=None,
            visual_confidence=0,
            severity=Severity.NONE.value,
            affected_area=AffectedArea.NONE.value,
            explanation_tamil=explanation_tamil,
            explanation_english=explanation_english,
            raw=data,
        )

    severity = str(data.get("severity", "")).strip().lower()
    area = str(data.get("affected_area", "")).strip().lower()
    primary = _nutrient(data.get("primary_deficiency"))
    secondary = _nutrient(data.get("secondary_deficiency"))
    if secondary == primary:
        secondary = None

    return NutrientObservation(
        plant_present=True,
        reject_reason=None,
        crop=str(data.get("crop", "")).strip() or "unknown",
        visible_symptoms=_symptoms(data.get("visible_symptoms")),
        primary=primary,
        secondary=secondary,
        visual_confidence=_bounded_int(data.get("confidence")) or 0,
        severity=severity if severity in _VALID_SEVERITIES else Severity.UNKNOWN.value,
        affected_area=area if area in _VALID_AREAS else AffectedArea.UNKNOWN.value,
        explanation_tamil=explanation_tamil,
        explanation_english=explanation_english,
        raw=data,
    )
