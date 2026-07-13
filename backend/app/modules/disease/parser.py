"""Structured validation of the vision response (docs: STEP 5). Pure, tested.

Rejects malformed JSON, missing crop/disease, and invalid confidence. The service
retries once on failure.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.modules.disease.constants import Severity


class AnalysisParseError(ValueError):
    """Raised when the model output is malformed or missing required fields."""


@dataclass
class DiseaseAnalysis:
    plant_present: bool
    reject_reason: str | None
    visible_parts: list[str]
    crop: str
    crop_confidence: int
    disease: str
    confidence: int
    severity: str
    symptoms: list[str]
    causes: list[str]
    recommendations: list[str]
    prevention: list[str]
    needs_expert_review: bool
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
        raise AnalysisParseError("no JSON object found")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AnalysisParseError(str(exc)) from exc
    if not isinstance(data, dict):
        raise AnalysisParseError("response is not a JSON object")
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


def _severity(value: Any) -> str:
    text = str(value).strip().lower()
    valid = {member.value for member in Severity}
    return text if text in valid else Severity.LOW.value


def parse_analysis(text: str) -> DiseaseAnalysis:
    data = _extract_json(text)
    plant_present = bool(data.get("plant_present", True))
    reject = data.get("reject_reason")
    reject_reason = str(reject).strip().lower() if reject else None
    explanation_tamil = str(data.get("explanation_tamil", "")).strip()
    explanation_english = str(data.get("explanation_english", "")).strip()

    if not plant_present:
        return DiseaseAnalysis(
            plant_present=False,
            reject_reason=reject_reason,
            visible_parts=_str_list(data.get("visible_parts")),
            crop="unknown",
            crop_confidence=0,
            disease="",
            confidence=0,
            severity=Severity.NONE.value,
            symptoms=[],
            causes=[],
            recommendations=[],
            prevention=[],
            needs_expert_review=True,
            explanation_tamil=explanation_tamil,
            explanation_english=explanation_english,
            raw=data,
        )

    crop = str(data.get("crop", "")).strip()
    disease = str(data.get("disease", "")).strip()
    confidence = _bounded_int(data.get("confidence"))
    if not crop or not disease or confidence is None:
        raise AnalysisParseError("missing crop/disease or invalid confidence")

    return DiseaseAnalysis(
        plant_present=True,
        reject_reason=None,
        visible_parts=_str_list(data.get("visible_parts")),
        crop=crop,
        crop_confidence=_bounded_int(data.get("crop_confidence")) or 0,
        disease=disease,
        confidence=confidence,
        severity=_severity(data.get("severity")),
        symptoms=_str_list(data.get("symptoms")),
        causes=_str_list(data.get("causes")),
        recommendations=_str_list(data.get("recommendations")),
        prevention=_str_list(data.get("prevention")),
        needs_expert_review=bool(data.get("needs_expert_review", False)),
        explanation_tamil=explanation_tamil,
        explanation_english=explanation_english,
        raw=data,
    )
