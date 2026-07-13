"""Farm-memory context builder (docs/AI_PROMPTS.md → AI CONTEXT).

Assembles the personalised context sent to the model so the farmer never has to
repeat known details. Pure function over already-loaded records — unit-tested.
"""
from __future__ import annotations

from app.modules.auth.profile_models import FarmerProfile
from app.modules.farms.models import Farm
from app.modules.weather.schemas import WeatherBundle


def _line(label: str, value: object | None) -> str | None:
    if value is None or value == "":
        return None
    return f"- {label}: {value}"


def build_farm_memory(
    profile: FarmerProfile | None,
    farm: Farm | None,
    weather: WeatherBundle | None,
) -> str:
    """Return a compact context block describing the farmer, farm and weather."""
    sections: list[str] = []

    if profile is not None:
        crops = [c for c in (profile.primary_crop, profile.secondary_crop) if c]
        farmer_lines = [
            _line("Name", profile.full_name),
            _line("District", profile.district),
            _line("Block", profile.block),
            _line("Village", profile.village),
            _line("Experience (years)", profile.experience_years),
            _line("Preferred crops", ", ".join(crops) if crops else None),
        ]
        farmer = [line for line in farmer_lines if line]
        if farmer:
            sections.append("Farmer:\n" + "\n".join(farmer))

    if farm is not None:
        location = farm.location
        farm_lines = [
            _line("Farm name", farm.name),
            _line("Crop", farm.crop),
            _line("Variety", farm.crop_variety),
            _line("Area (hectares)", farm.area_hectares),
            _line("Soil type", farm.soil_type),
            _line("Irrigation", farm.irrigation_type),
            _line("Water source", farm.water_source),
            _line("Sowing date", farm.sowing_date),
            _line("Status", farm.status),
            _line("District", location.district if location else None),
            _line("Village", location.village if location else None),
        ]
        details = [line for line in farm_lines if line]
        if details:
            sections.append("Current farm:\n" + "\n".join(details))

    if weather is not None:
        current = weather.current
        top = weather.insights[0] if weather.insights else None
        weather_lines = [
            _line("Condition", current.condition),
            _line("Temperature (°C)", current.temperature_c),
            _line("Humidity (%)", current.humidity_pct),
            _line("Wind (km/h)", current.wind_speed_kmh),
            _line(
                "Rain chance today (%)",
                weather.daily[0].precipitation_probability_max_pct
                if weather.daily
                else None,
            ),
            _line("Today's advisory", top.message if top else None),
        ]
        details = [line for line in weather_lines if line]
        if details:
            sections.append("Verified weather (from Open-Meteo):\n" + "\n".join(details))

    if not sections:
        return "No saved farm details yet. Ask the farmer for the details you need."
    return "\n\n".join(sections)
