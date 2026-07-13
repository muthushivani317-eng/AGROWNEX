"""Normalized module signals (pure inputs to the Crop Intelligence Engine).

The service builds these from each module's own repository/service (guarded — one
module failing is never fatal, and it is never modified). Every field a module can't
supply stays ``None`` so the engine reduces confidence instead of inventing a value.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiseaseSignal:
    disease: str | None
    confidence: int | None
    severity: str | None       # none | low | moderate | high
    needs_expert: bool = False


@dataclass(frozen=True)
class NutrientSignal:
    primary: str | None
    status: str | None         # confirmed | possible | not_confirmed
    confidence: int | None
    severity: str | None       # none | mild | moderate | severe | unknown
    needs_test: bool = False


@dataclass(frozen=True)
class SoilSignal:
    has_data: bool
    nitrogen: str | None = None      # low | medium | high | unknown
    phosphorus: str | None = None
    potassium: str | None = None
    organic_carbon: str | None = None
    ph_class: str | None = None
    salinity: str | None = None
    deficient_micronutrients: tuple[str, ...] = ()
    confidence: int | None = None


@dataclass(frozen=True)
class SatelliteSignal:
    ndvi: float | None
    vegetation_health: str | None
    stress_level: str | None
    moisture_status: str | None
    trend: str | None
    confidence: int | None = None
    alert_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class WeatherSignal:
    insight_codes: tuple[str, ...] = ()
    daily_min_temp_c: float | None = None
    daily_max_temp_c: float | None = None
    rain_probability_pct: int | None = None


@dataclass(frozen=True)
class GrowthSignal:
    health_score: int | None
    health_delta: int | None
    risk_level: str | None     # low | medium | high


@dataclass(frozen=True)
class CalendarSignal:
    today: int = 0
    upcoming: int = 0
    missed: int = 0


@dataclass(frozen=True)
class ExpertSignal:
    open_consultation: bool = False


@dataclass(frozen=True)
class IntelligenceInputs:
    """Everything the engine needs. Any module may be ``None`` (absent)."""

    disease: DiseaseSignal | None = None
    nutrient: NutrientSignal | None = None
    soil: SoilSignal | None = None
    satellite: SatelliteSignal | None = None
    weather: WeatherSignal | None = None
    growth: GrowthSignal | None = None
    calendar: CalendarSignal = field(default_factory=CalendarSignal)
    expert: ExpertSignal = field(default_factory=ExpertSignal)
