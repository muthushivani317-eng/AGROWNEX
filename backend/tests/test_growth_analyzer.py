"""Unit tests for the growth analyzer (parsing + mock + retry, no network)."""
from __future__ import annotations

import json

import pytest
from app.modules.growth.analyzer import (
    GeminiGrowthProvider,
    GrowthAnalysisParseError,
    GrowthAnalysisRequest,
    MockGrowthProvider,
    UnavailableGrowthProvider,
    get_default_provider,
    parse_growth_analysis,
)
from app.modules.growth.exceptions import GrowthAnalysisError

_GOOD = json.dumps(
    {
        "plant_present": True,
        "growth_stage": "vegetative",
        "plant_vigor": "good",
        "health_score": 82,
        "confidence": 74,
        "leaf_color_observations": ["green"],
        "visible_abnormalities": ["slight yellowing"],
        "changes_from_previous": ["taller"],
        "recommendations": ["irrigate"],
        "needs_expert_review": False,
        "growth_summary_tamil": "வளர்ச்சி நன்று",
        "growth_summary_english": "growing well",
    }
)


def test_parse_good_response() -> None:
    result = parse_growth_analysis(_GOOD)
    assert result.plant_present is True
    assert result.growth_stage == "vegetative"
    assert result.plant_vigor == "good"
    assert result.health_score == 82
    assert result.leaf_color_observations == ["green"]
    assert result.changes_from_previous == ["taller"]


def test_parse_clamps_and_defaults_unknown_enums() -> None:
    raw = json.dumps(
        {
            "plant_present": True,
            "growth_stage": "banana-time",  # invalid → unknown
            "plant_vigor": "amazing",  # invalid → unknown
            "health_score": 250,  # clamped to 100
            "confidence": -5,  # clamped to 0
            "growth_summary_tamil": "x",
            "growth_summary_english": "y",
        }
    )
    result = parse_growth_analysis(raw)
    assert result.growth_stage == "unknown"
    assert result.plant_vigor == "unknown"
    assert result.health_score == 100
    assert result.confidence == 0


def test_parse_plant_absent() -> None:
    result = parse_growth_analysis(
        json.dumps({"plant_present": False, "reject_reason": "Building"})
    )
    assert result.plant_present is False
    assert result.reject_reason == "building"
    assert result.needs_expert_review is True


def test_parse_rejects_non_json() -> None:
    with pytest.raises(GrowthAnalysisParseError):
        parse_growth_analysis("no json here")


async def test_mock_provider_returns_result() -> None:
    provider = MockGrowthProvider()
    result = await provider.analyze(
        GrowthAnalysisRequest(
            image_base64="x",
            mime_type="image/jpeg",
            crop="paddy",
            language="ta",
            farm_context="",
        )
    )
    assert result.plant_present is True
    assert result.growth_stage == "vegetative"
    assert result.growth_summary_tamil  # Tamil-first summary present


async def test_mock_provider_notes_changes_when_previous_context() -> None:
    provider = MockGrowthProvider()
    result = await provider.analyze(
        GrowthAnalysisRequest(
            image_base64="x",
            mime_type="image/jpeg",
            crop="paddy",
            language="en",
            farm_context="",
            previous_context="Week 1: stage=seedling, health=70",
        )
    )
    assert result.changes_from_previous  # comparison populated


def test_default_provider_fails_closed_without_key(monkeypatch) -> None:
    monkeypatch.delenv("AGROWAI_ENABLE_TEST_MOCKS", raising=False)
    assert isinstance(get_default_provider(), UnavailableGrowthProvider)


def test_default_provider_allows_explicit_mock_only_in_development(monkeypatch) -> None:
    # Uses the shared app.core.provider_policy.test_mocks_enabled() guard now
    # (APP_ENV, falling back to ENVIRONMENT, plus an explicit opt-in flag) --
    # the same one every other module's mock provider uses -- instead of a
    # growth-specific GROWTH_PROVIDER env var that only checked ENVIRONMENT
    # and would silently mis-gate if ops only set the documented APP_ENV
    # (2026-08 pre-release audit).
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AGROWAI_ENABLE_TEST_MOCKS", "true")
    assert isinstance(get_default_provider(), MockGrowthProvider)

    monkeypatch.setenv("APP_ENV", "production")
    assert isinstance(get_default_provider(), UnavailableGrowthProvider)


class RetryGrowth(GeminiGrowthProvider):
    def __init__(self, outputs: list[str]) -> None:
        super().__init__(api_key="test-key")
        self._outputs = outputs
        self._index = 0

    async def _generate(self, request) -> str:  # type: ignore[override]
        out = self._outputs[self._index]
        self._index += 1
        return out


async def test_gemini_retries_once_on_bad_json() -> None:
    provider = RetryGrowth(["not json", _GOOD])
    result = await provider.analyze(
        GrowthAnalysisRequest(
            image_base64="x",
            mime_type="image/jpeg",
            crop="paddy",
            language="ta",
            farm_context="",
        )
    )
    assert result.health_score == 82
    assert provider._index == 2  # retried exactly once


async def test_gemini_gives_up_after_retry() -> None:
    provider = RetryGrowth(["bad", "still bad"])
    with pytest.raises(GrowthAnalysisError):
        await provider.analyze(
            GrowthAnalysisRequest(
                image_base64="x",
                mime_type="image/jpeg",
                crop=None,
                language="en",
                farm_context="",
            )
        )
