from __future__ import annotations

import io
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from PIL import Image, UnidentifiedImageError

from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.auth.dependencies import ControlledTester

from .provider import (
    PlantIdentifierProvider,
    PlantIdentifierProviderError,
    get_plant_identifier_provider,
)
from .schemas import PlantIdentificationResponse
from .service import (
    InvalidPlantIdentifierResponseError,
    failure_response,
    parse_plant_identification,
    response_from_identification,
)

router = APIRouter(prefix="/plant-identifier", tags=["plant-identifier"])
MAX_IMAGE_BYTES = 12_000_000
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def get_configured_provider() -> PlantIdentifierProvider | None:
    try:
        return get_plant_identifier_provider()
    except PlantIdentifierProviderError:
        return None


ProviderDep = Annotated[PlantIdentifierProvider | None, Depends(get_configured_provider)]


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "") or uuid.uuid4())


async def _validated_image(upload: UploadFile) -> tuple[bytes, str, str | None]:
    if upload.content_type not in ALLOWED_TYPES:
        await upload.close()
        return b"", "", "IMAGE_FORMAT_UNSUPPORTED"
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if len(data) > MAX_IMAGE_BYTES:
        return b"", "", "IMAGE_SIZE_INVALID"
    if not data:
        return b"", "", "CORRUPT_OR_INVALID_IMAGE"
    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
        image = Image.open(io.BytesIO(data))
        image.load()
        require_safe_image(image)
    except UnsafeImageError as exc:
        return b"", "", exc.reason_code
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return b"", "", "CORRUPT_OR_INVALID_IMAGE"
    return data, upload.content_type, None


@router.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "internal_testing",
        "provider": "gemini",
        "configured": get_configured_provider() is not None,
        "informational_only": True,
        "used_for_disease_routing": False,
        "general_farmer_release_authorized": False,
    }


@router.post("/identify", response_model=PlantIdentificationResponse)
async def identify_plant(
    request: Request,
    tester: ControlledTester,
    provider: ProviderDep,
    image: UploadFile = File(...),
    preferred_language: Literal["ta", "en"] = Form("ta"),
    user_note: str | None = Form(default=None, max_length=300),
) -> PlantIdentificationResponse:
    del tester
    request_id = _request_id(request)
    data, mime_type, error = await _validated_image(image)
    if error:
        return failure_response(
            request_id=request_id,
            language=preferred_language,
            status="invalid_image",
            error_code="PLANT_IDENTIFIER_INVALID_IMAGE",
            retry_allowed=True,
        )
    if provider is None:
        return failure_response(
            request_id=request_id,
            language=preferred_language,
            status="provider_error",
            error_code="PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE",
            retry_allowed=True,
        )
    try:
        raw = await provider.identify(data, mime_type, preferred_language, user_note)
        parsed = parse_plant_identification(raw)
        return response_from_identification(
            parsed, request_id=request_id, language=preferred_language
        )
    except InvalidPlantIdentifierResponseError:
        return failure_response(
            request_id=request_id,
            language=preferred_language,
            status="provider_error",
            error_code="PLANT_IDENTIFIER_INVALID_PROVIDER_RESPONSE",
            retry_allowed=True,
        )
    except PlantIdentifierProviderError as exc:
        safe_code = str(exc)
        if safe_code not in {
            "PLANT_IDENTIFIER_PROVIDER_TIMEOUT",
            "PLANT_IDENTIFIER_PROVIDER_RATE_LIMIT",
            "PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE",
            "PLANT_IDENTIFIER_INVALID_PROVIDER_RESPONSE",
        }:
            safe_code = "PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE"
        return failure_response(
            request_id=request_id,
            language=preferred_language,
            status="provider_error",
            error_code=safe_code,
            retry_allowed=True,
        )
    except Exception:
        return failure_response(
            request_id=request_id,
            language=preferred_language,
            status="provider_error",
            error_code="PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE",
            retry_allowed=True,
        )
