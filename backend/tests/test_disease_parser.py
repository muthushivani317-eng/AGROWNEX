"""Unit tests for the analysis parser / structured validation (docs: STEP 5)."""
from __future__ import annotations

import json

import pytest
from app.modules.disease.parser import AnalysisParseError, parse_analysis

_VALID = {
    "plant_present": True,
    "reject_reason": None,
    "visible_parts": ["leaf"],
    "crop": "paddy",
    "crop_confidence": 85,
    "disease": "Leaf blast",
    "confidence": 78,
    "severity": "moderate",
    "symptoms": ["grey lesions"],
    "causes": ["fungus"],
    "recommendations": ["remove affected leaves"],
    "prevention": ["treat seeds"],
    "needs_expert_review": False,
    "explanation_tamil": "விளக்கம்",
    "explanation_english": "explanation",
}


def test_parses_a_valid_response():
    result = parse_analysis(json.dumps(_VALID))
    assert result.plant_present is True
    assert result.crop == "paddy"
    assert result.disease == "Leaf blast"
    assert result.confidence == 78
    assert result.severity == "moderate"
    assert result.symptoms == ["grey lesions"]


def test_strips_code_fences():
    fenced = "```json\n" + json.dumps(_VALID) + "\n```"
    assert parse_analysis(fenced).crop == "paddy"


def test_no_plant_is_valid_without_crop():
    payload = {
        "plant_present": False,
        "reject_reason": "building",
        "explanation_tamil": "செடி இல்லை",
        "explanation_english": "no plant",
    }
    result = parse_analysis(json.dumps(payload))
    assert result.plant_present is False
    assert result.reject_reason == "building"
    assert result.needs_expert_review is True


def test_malformed_json_raises():
    with pytest.raises(AnalysisParseError):
        parse_analysis("this is not json")


def test_missing_fields_raise():
    for bad in [
        {**_VALID, "crop": ""},
        {**_VALID, "disease": ""},
        {**_VALID, "confidence": "high"},
        {**_VALID, "confidence": 250},
    ]:
        with pytest.raises(AnalysisParseError):
            parse_analysis(json.dumps(bad))


def test_invalid_severity_defaults_to_low():
    result = parse_analysis(json.dumps({**_VALID, "severity": "catastrophic"}))
    assert result.severity == "low"
