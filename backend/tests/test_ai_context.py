"""Unit tests for the AI context builder, prompts and validator (pure)."""
from __future__ import annotations

from types import SimpleNamespace

from app.modules.ai.constants import MAX_RESPONSE_CHARS
from app.modules.ai.context import build_farm_memory
from app.modules.ai.prompts import build_system_instruction
from app.modules.ai.provider import MockAIProvider
from app.modules.ai.validator import validate_response


def _profile():
    return SimpleNamespace(
        full_name="Muthu Kumar",
        district="madurai",
        block="Melur",
        village=None,
        experience_years=8,
        primary_crop="paddy",
        secondary_crop="sugarcane",
        language="ta",
    )


def _farm():
    return SimpleNamespace(
        name="Riverside",
        crop="paddy",
        crop_variety="ADT 43",
        area_hectares=1.2,
        soil_type="alluvial",
        irrigation_type="canal",
        water_source="river",
        sowing_date=None,
        status="active",
        location=SimpleNamespace(district="madurai", village="Kottampatti"),
    )


def test_build_farm_memory_includes_known_details():
    memory = build_farm_memory(_profile(), _farm(), None)
    assert "Muthu Kumar" in memory
    assert "Riverside" in memory
    assert "paddy" in memory
    assert "alluvial" in memory


def test_build_farm_memory_empty():
    memory = build_farm_memory(None, None, None)
    assert "No saved farm details" in memory


def test_build_farm_memory_includes_weather():
    weather = SimpleNamespace(
        current=SimpleNamespace(
            condition="rain",
            temperature_c=29.0,
            humidity_pct=80,
            wind_speed_kmh=12.0,
        ),
        daily=[SimpleNamespace(precipitation_probability_max_pct=70)],
        insights=[SimpleNamespace(message="Rain expected — hold irrigation.")],
    )
    memory = build_farm_memory(None, None, weather)
    assert "rain" in memory
    assert "Rain expected" in memory


def test_system_instruction_language_directive():
    tamil = build_system_instruction("ta", "context here")
    assert "Tamil" in tamil
    assert "context here" in tamil
    english = build_system_instruction("en", "ctx")
    assert "English" in english


def test_validate_response_trims_and_falls_back():
    assert validate_response("  hello  ", "en") == "hello"
    assert "agriculture officer" in validate_response("", "en")
    assert validate_response("", "ta")  # non-empty Tamil fallback
    long_text = "x" * (MAX_RESPONSE_CHARS + 500)
    assert len(validate_response(long_text, "en")) == MAX_RESPONSE_CHARS


async def test_mock_provider_language_switch():
    provider = MockAIProvider()
    ta = await provider.generate(
        system=build_system_instruction("ta", ""), history=[], message="test"
    )
    en = await provider.generate(
        system=build_system_instruction("en", ""), history=[], message="test"
    )
    assert "டெமோ" in ta.text  # Tamil demo marker
    assert "demo response" in en.text
    assert ta.model == "mock-gemini"
