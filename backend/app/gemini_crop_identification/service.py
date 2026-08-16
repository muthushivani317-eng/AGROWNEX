from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .schemas import GeminiCropIdentification

SUPPORTED_CROPS = frozenset({"banana", "paddy", "cotton", "groundnut", "redgram", "chilli"})
IDENTIFICATION_THRESHOLD = 0.90
CROP_ID_VERSION = "temporary-gemini-v1"


class InvalidGeminiCropResponseError(ValueError):
    pass


def parse_crop_identification(raw: str) -> GeminiCropIdentification:
    try:
        data: Any = json.loads(raw)
        if not isinstance(data, dict):
            raise TypeError
        parsed = GeminiCropIdentification.model_validate(data)
    except (json.JSONDecodeError, TypeError, ValidationError) as exc:
        raise InvalidGeminiCropResponseError("INVALID_GEMINI_SCHEMA") from exc

    # Gemini confidence is a self-report, not calibrated probability. It may only
    # decide whether to fail closed; it is never presented as model accuracy.
    if parsed.status == "identified" and (
        parsed.confidence is None or parsed.confidence < IDENTIFICATION_THRESHOLD
    ):
        return parsed.model_copy(
            update={
                "status": "uncertain",
                "crop_id": None,
                "reason_code": "CROP_IDENTIFICATION_UNCERTAIN",
                "needs_another_image": True,
            }
        )
    return parsed
