from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from .schemas import GeminiPlantIdentification, PlantIdentificationResponse

DISCLAIMER = (
    "This identification is provided for general knowledge only. Do not use it "
    "as a disease diagnosis, treatment recommendation, or proof that a plant is "
    "safe to eat, touch, or use."
)
DISCLAIMER_TA = (
    "இந்த அடையாளம் பொதுத் தகவலுக்காக மட்டுமே வழங்கப்படுகிறது. இதை நோய் "
    "கண்டறிதல், சிகிச்சைப் பரிந்துரை அல்லது ஒரு தாவரத்தை உண்ண, தொட, அல்லது "
    "பயன்படுத்த பாதுகாப்பானது என்பதற்கான சான்றாக பயன்படுத்த வேண்டாம்."
)
MAX_PROVIDER_RESPONSE_CHARS = 20_000
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


class InvalidPlantIdentifierResponseError(ValueError):
    pass


def parse_plant_identification(raw: str) -> GeminiPlantIdentification:
    if not isinstance(raw, str) or not raw.strip():
        raise InvalidPlantIdentifierResponseError("EMPTY_PROVIDER_RESPONSE")
    if len(raw) > MAX_PROVIDER_RESPONSE_CHARS:
        raise InvalidPlantIdentifierResponseError("OVERSIZED_PROVIDER_RESPONSE")
    match = _FENCE.match(raw)
    candidate = match.group(1) if match else raw
    try:
        data: Any = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise InvalidPlantIdentifierResponseError("MALFORMED_PROVIDER_JSON") from exc
    if not isinstance(data, dict):
        raise InvalidPlantIdentifierResponseError("INVALID_PROVIDER_SCHEMA")
    try:
        return GeminiPlantIdentification.model_validate(data)
    except ValidationError as exc:
        raise InvalidPlantIdentifierResponseError("INVALID_PROVIDER_SCHEMA") from exc


def response_from_identification(
    parsed: GeminiPlantIdentification, *, request_id: str, language: str
) -> PlantIdentificationResponse:
    error_code = {
        "uncertain": "PLANT_IDENTIFIER_UNCERTAIN",
        "non_plant": "PLANT_IDENTIFIER_NON_PLANT",
    }.get(parsed.status)
    return PlantIdentificationResponse(
        request_id=request_id,
        **parsed.model_dump(),
        language=language,
        disclaimer=DISCLAIMER_TA if language == "ta" else DISCLAIMER,
        processing_status="complete",
        error_code=error_code,
        retry_allowed=parsed.status != "identified",
    )


def failure_response(
    *,
    request_id: str,
    language: str,
    status: str,
    error_code: str,
    retry_allowed: bool,
) -> PlantIdentificationResponse:
    return PlantIdentificationResponse(
        request_id=request_id,
        status=status,
        confidence=0.0,
        language=language,
        disclaimer=DISCLAIMER_TA if language == "ta" else DISCLAIMER,
        processing_status="rejected" if status == "invalid_image" else "failed",
        error_code=error_code,
        retry_allowed=retry_allowed,
    )
