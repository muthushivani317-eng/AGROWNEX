from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class LccAnalyzeRequest(BaseModel):
    farm_id: uuid.UUID
    image_base64: str = Field(min_length=4, max_length=12_000_000)
    mime_type: Literal["image/jpeg", "image/png", "image/webp"]


class LccAnalysisOut(BaseModel):
    farm_id: uuid.UUID
    crop: str | None
    abstained: bool
    quality_issue: str | None
    panel_number: int | None
    nitrogen_status: Literal["deficient", "borderline", "sufficient", "abstained"]
    guidance_key: str
    average_lab: tuple[float, float, float] | None
    color_distance: float | None
    leaf_pixel_ratio: float
    brightness: float
    sharpness: float
    method: Literal["cie76"] = "cie76"
    is_estimate: bool = True
