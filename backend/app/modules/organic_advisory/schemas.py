from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.action_verification.schemas import ActionOut

WeatherGateSignal = Literal[
    "spraying.avoid_rain",
    "spraying.avoid_wind",
    "heavy_rain.expected",
    "heavy_rain.severe",
]


class WeatherOrganicGateIn(BaseModel):
    farm_id: uuid.UUID
    action_workflow_id: uuid.UUID
    organic_input_id: uuid.UUID
    signal_code: WeatherGateSignal
    forecast_observed_at: datetime
    forecast_valid_until: datetime
    safe_after: datetime
    forecast_source: str = Field(min_length=1, max_length=40)
    forecast_version: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def valid_window(self):
        if not (self.forecast_observed_at < self.safe_after <= self.forecast_valid_until):
            raise ValueError("INVALID_WEATHER_GATE_WINDOW")
        return self


class WeatherOrganicGateOut(BaseModel):
    original_action_id: uuid.UUID
    gate_action: ActionOut
    decision: Literal["postpone"] = "postpone"
    explanation: str


class TrustedWeatherGateIn(BaseModel):
    farm_id: uuid.UUID
    action_workflow_id: uuid.UUID
    organic_input_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=100)


class TrustedWeatherGateOut(BaseModel):
    original_action_id: uuid.UUID
    weather_snapshot_id: uuid.UUID
    reschedule_id: uuid.UUID | None
    notification_intent_id: uuid.UUID | None
    signal_code: str | None
    rescheduled_for: datetime | None
    source_verified: bool
    data_state: str


class OrganicWeatherMetricsOut(BaseModel):
    farm_id: uuid.UUID
    snapshot_count: int
    reschedule_count: int
    pending_notification_intents: int


class SatelliteScoutingIn(BaseModel):
    farm_id: uuid.UUID
    satellite_alert_id: uuid.UUID
    expires_at: datetime


class SatelliteScoutingOut(BaseModel):
    action: ActionOut
    trigger: str
    scene_id: str
    checklist: list[str]
    limitation: str


class SatelliteFindingIn(BaseModel):
    observations: list[
        Literal[
            "visible_pest_or_disease_symptoms",
            "visible_nutrient_symptoms",
            "weed_pressure",
            "dry_soil",
            "waterlogging",
            "mulch_gap",
            "uneven_amendment",
            "physical_damage",
            "nothing_observed",
        ]
    ] = Field(min_length=1, max_length=9)
    note: str | None = Field(default=None, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=100)

    @model_validator(mode="after")
    def nothing_is_exclusive(self):
        if "nothing_observed" in self.observations and len(self.observations) != 1:
            raise ValueError("NOTHING_OBSERVED_MUST_BE_EXCLUSIVE")
        return self


class SatelliteFindingOut(BaseModel):
    log_entry_id: uuid.UUID
    follow_up_action: ActionOut | None
    farmer_reported: bool = True
    diagnosis: None = None
