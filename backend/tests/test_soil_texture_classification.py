"""classify_texture_bucket (app/modules/soil/engine.py) -- a pure, conservative
mapping from a clay/sand/silt composition (e.g. SoilGrids' remote estimate)
onto this app's own farmer-registered SoilType vocabulary (sandy/clay/loamy/
silt). Added 2026-08-19 alongside the Soil Scan texture fallback.
"""

from __future__ import annotations

from app.modules.farms.constants import SoilType
from app.modules.soil.engine import classify_texture_bucket


def test_missing_any_input_returns_none_never_invented() -> None:
    assert classify_texture_bucket(None, 40, 30) is None
    assert classify_texture_bucket(30, None, 30) is None
    assert classify_texture_bucket(30, 40, None) is None


def test_high_clay_classifies_as_clay() -> None:
    assert classify_texture_bucket(45, 30, 25) == SoilType.CLAY.value


def test_high_silt_low_clay_classifies_as_silt() -> None:
    assert classify_texture_bucket(8, 10, 82) == SoilType.SILT.value


def test_high_sand_low_clay_classifies_as_sandy() -> None:
    assert classify_texture_bucket(10, 75, 15) == SoilType.SANDY.value


def test_balanced_composition_classifies_as_loamy() -> None:
    assert classify_texture_bucket(25, 40, 35) == SoilType.LOAMY.value


def test_high_silt_but_borderline_clay_falls_back_to_loamy() -> None:
    """Silt alone isn't enough near the boundary -- clay must also be low,
    otherwise this is a silty clay, not a pure Silt texture."""
    assert classify_texture_bucket(20, 5, 75) == SoilType.LOAMY.value


def test_high_sand_but_borderline_clay_falls_back_to_loamy() -> None:
    """Sand alone isn't enough near the boundary -- clay must also be low,
    otherwise this is a sandy clay, not a pure Sand texture."""
    assert classify_texture_bucket(20, 72, 8) == SoilType.LOAMY.value
