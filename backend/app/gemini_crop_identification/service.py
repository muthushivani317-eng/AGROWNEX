from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .schemas import CropIdentificationResponse, GeminiCropIdentification

SUPPORTED_CROPS = frozenset(
    {"banana", "paddy", "cotton", "groundnut", "redgram", "chilli"}
)
IDENTIFICATION_THRESHOLD = 0.90


class InvalidGeminiCropResponseError(ValueError):
    pass


def parse_crop_identification(raw: str) -> CropIdentificationResponse:
    try:
        data: Any = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise InvalidGeminiCropResponseError("MALFORMED_GEMINI_JSON") from exc
    if not isinstance(data, dict):
        raise InvalidGeminiCropResponseError("INVALID_GEMINI_SCHEMA")

    crop_id = data.get("crop_id")
    if crop_id is None:
        raise InvalidGeminiCropResponseError("MISSING_CROP_ID")

    # An unsupported name is never allowed into the disease registry.
    if crop_id not in SUPPORTED_CROPS | {"unknown", "non_plant"}:
        data.update(
            status="uncertain",
            crop_id="unknown",
            confidence=0.0,
            needs_another_image=True,
        )

    try:
        parsed = GeminiCropIdentification.model_validate(data)
    except ValidationError as exc:
        raise InvalidGeminiCropResponseError("INVALID_GEMINI_SCHEMA") from exc

    if parsed.status == "non_plant":
        parsed = parsed.model_copy(
            update={"crop_id": "non_plant", "needs_another_image": True}
        )
    elif (
        parsed.status != "identified"
        or parsed.crop_id not in SUPPORTED_CROPS
        or parsed.confidence < IDENTIFICATION_THRESHOLD
    ):
        parsed = parsed.model_copy(
            update={
                "status": "uncertain",
                "crop_id": "unknown",
                "needs_another_image": True,
            }
        )
    return CropIdentificationResponse(**parsed.model_dump())
