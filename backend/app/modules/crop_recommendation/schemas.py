from __future__ import annotations

from pydantic import BaseModel, Field


class CropRecommendationRequest(BaseModel):
    nitrogen: float = Field(ge=0, le=200)
    phosphorus: float = Field(ge=0, le=200)
    potassium: float = Field(ge=0, le=250)
    temperature_c: float = Field(ge=-10, le=60)
    humidity_percent: float = Field(ge=0, le=100)
    ph: float = Field(ge=0, le=14)
    rainfall_mm: float = Field(ge=0, le=2000)


class RankedCrop(BaseModel):
    crop: str
    model_probability: float


class CropRecommendationResponse(BaseModel):
    status: str = "provisional_controlled_test"
    recommended_crop: str
    model_probability: float
    alternatives: list[RankedCrop]
    model_version: str = "controlled_crop_recommendation_v1"
    validation_status: str = "NO_INDEPENDENT_AGROWAI_EVALUATION"
    test_mode: bool = True
    general_farmer_release_authorized: bool = False
    disclaimer: str
