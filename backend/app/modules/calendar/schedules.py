"""Predefined crop schedules (docs: Calendar Generation — deterministic, no AI).

Each template is an activity offset (in days) from the sowing date. Codes are
stable so the frontend can localize titles/descriptions (Tamil-first); the English
title/description here are the fallback and are used for logs/future AI.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.modules.calendar.constants import (
    ActivityType,
    GrowthStage,
    Priority,
    WeatherDependency,
)


@dataclass(frozen=True)
class ActivityTemplate:
    code: str
    activity_type: ActivityType
    day_offset: int
    priority: Priority
    growth_stage: GrowthStage
    weather_dependency: WeatherDependency
    reminder_enabled: bool
    title: str
    description: str


_T = ActivityTemplate
_AT = ActivityType
_P = Priority
_G = GrowthStage
_W = WeatherDependency

# A generic ~120-day crop schedule; used when a crop has no specific schedule.
DEFAULT_SCHEDULE: list[ActivityTemplate] = [
    _T("land_prep", _AT.LAND_PREPARATION, -12, _P.HIGH, _G.LAND_PREP, _W.NONE, True,
       "Land preparation", "Plough and level the field and add farmyard manure."),
    _T("seed_treatment", _AT.SEED_TREATMENT, -2, _P.MEDIUM, _G.LAND_PREP, _W.NONE, True,
       "Seed treatment", "Treat seeds with a recommended bio-agent or fungicide."),
    _T("sowing", _AT.SOWING, 0, _P.HIGH, _G.SEEDLING, _W.NONE, True,
       "Sowing", "Sow seeds at the recommended spacing and depth."),
    _T("fertilizer_basal", _AT.FERTILIZER, 1, _P.MEDIUM, _G.SEEDLING, _W.NONE, True,
       "Basal fertilizer", "Apply the basal dose of fertilizer as per soil test."),
    _T("irrigation_1", _AT.IRRIGATION, 3, _P.HIGH, _G.SEEDLING, _W.IRRIGATION, True,
       "First irrigation", "Give a light irrigation to aid germination."),
    _T("weeding_1", _AT.WEED_MANAGEMENT, 20, _P.MEDIUM, _G.VEGETATIVE, _W.NONE, True,
       "First weeding", "Remove weeds to reduce competition for nutrients."),
    _T("irrigation_2", _AT.IRRIGATION, 22, _P.MEDIUM, _G.VEGETATIVE, _W.IRRIGATION, True,
       "Irrigation", "Irrigate based on soil moisture."),
    _T("fertilizer_top", _AT.FERTILIZER, 30, _P.MEDIUM, _G.VEGETATIVE, _W.NONE, True,
       "Top dressing", "Apply the top-dressing nitrogen fertilizer."),
    _T("pest_monitoring", _AT.PEST_MONITORING, 35, _P.MEDIUM, _G.VEGETATIVE, _W.SPRAYING, True,
       "Pest monitoring", "Scout for pests; spray only if the threshold is crossed."),
    _T("disease_inspection", _AT.DISEASE_INSPECTION, 45, _P.MEDIUM, _G.VEGETATIVE, _W.NONE, True,
       "Disease inspection", "Inspect leaves; use AgrowAI disease detection if unsure."),
    _T("flowering", _AT.FLOWERING_OBSERVATION, 55, _P.MEDIUM, _G.FLOWERING, _W.NONE, True,
       "Flowering check", "Observe flowering and ensure adequate soil moisture."),
    _T("irrigation_3", _AT.IRRIGATION, 60, _P.HIGH, _G.FLOWERING, _W.IRRIGATION, True,
       "Critical irrigation", "Flowering is moisture-critical — irrigate."),
    _T("harvest_prep", _AT.HARVEST_PREPARATION, 100, _P.MEDIUM, _G.MATURITY, _W.NONE, True,
       "Harvest preparation", "Arrange labour and equipment for harvest."),
    _T("harvest", _AT.HARVEST, 115, _P.HIGH, _G.HARVEST, _W.NONE, True,
       "Harvest", "Harvest at proper maturity, preferably in dry weather."),
    _T("post_harvest", _AT.POST_HARVEST, 120, _P.MEDIUM, _G.POST_HARVEST, _W.NONE, True,
       "Post-harvest", "Dry, clean and store the produce properly."),
]

# Paddy (~135 days) — a crop-specific schedule.
PADDY_SCHEDULE: list[ActivityTemplate] = [
    _T("land_prep", _AT.LAND_PREPARATION, -15, _P.HIGH, _G.LAND_PREP, _W.NONE, True,
       "Puddling & levelling", "Puddle and level the field; keep a thin water layer."),
    _T("seed_treatment", _AT.SEED_TREATMENT, -3, _P.MEDIUM, _G.LAND_PREP, _W.NONE, True,
       "Seed treatment", "Soak and treat seeds before nursery/sowing."),
    _T("sowing", _AT.SOWING, 0, _P.HIGH, _G.SEEDLING, _W.NONE, True,
       "Transplanting / sowing", "Transplant seedlings or sow at recommended spacing."),
    _T("fertilizer_basal", _AT.FERTILIZER, 1, _P.MEDIUM, _G.SEEDLING, _W.NONE, True,
       "Basal fertilizer", "Apply the basal NPK dose."),
    _T("irrigation_1", _AT.IRRIGATION, 3, _P.HIGH, _G.SEEDLING, _W.IRRIGATION, True,
       "Maintain water level", "Maintain a shallow water level for establishment."),
    _T("weeding_1", _AT.WEED_MANAGEMENT, 20, _P.MEDIUM, _G.VEGETATIVE, _W.NONE, True,
       "First weeding", "Remove weeds during early tillering."),
    _T("fertilizer_top", _AT.FERTILIZER, 30, _P.MEDIUM, _G.VEGETATIVE, _W.NONE, True,
       "Top dressing", "Apply nitrogen at active tillering."),
    _T("pest_monitoring", _AT.PEST_MONITORING, 40, _P.MEDIUM, _G.VEGETATIVE, _W.SPRAYING, True,
       "Pest monitoring", "Watch for stem borer and leaf folder."),
    _T("disease_inspection", _AT.DISEASE_INSPECTION, 50, _P.MEDIUM, _G.VEGETATIVE, _W.NONE, True,
       "Disease inspection", "Check for blast and blight symptoms."),
    _T("flowering", _AT.FLOWERING_OBSERVATION, 65, _P.MEDIUM, _G.FLOWERING, _W.NONE, True,
       "Panicle initiation", "Observe panicle initiation; ensure water."),
    _T("irrigation_3", _AT.IRRIGATION, 70, _P.HIGH, _G.FLOWERING, _W.IRRIGATION, True,
       "Critical irrigation", "Flowering is moisture-critical — do not let it dry."),
    _T("harvest_prep", _AT.HARVEST_PREPARATION, 120, _P.MEDIUM, _G.MATURITY, _W.NONE, True,
       "Harvest preparation", "Drain the field and arrange for harvest."),
    _T("harvest", _AT.HARVEST, 135, _P.HIGH, _G.HARVEST, _W.NONE, True,
       "Harvest", "Harvest when 80% of grains are straw-coloured."),
    _T("post_harvest", _AT.POST_HARVEST, 140, _P.MEDIUM, _G.POST_HARVEST, _W.NONE, True,
       "Post-harvest", "Thresh, dry to safe moisture and store."),
]

SCHEDULES: dict[str, list[ActivityTemplate]] = {
    "paddy": PADDY_SCHEDULE,
}


def get_schedule(crop: str | None) -> list[ActivityTemplate]:
    if crop and crop in SCHEDULES:
        return SCHEDULES[crop]
    return DEFAULT_SCHEDULE
