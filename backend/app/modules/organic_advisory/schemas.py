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
        if not (
            self.forecast_observed_at < self.safe_after <= self.forecast_valid_until
        ):
            raise ValueError("INVALID_WEATHER_GATE_WINDOW")
        return self


class WeatherOrganicGateOut(BaseModel):
    original_action_id: uuid.UUID
    gate_action: ActionOut
    decision: Literal["postpone"] = "postpone"
    explanation: str


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
