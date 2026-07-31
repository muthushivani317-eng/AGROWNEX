from __future__ import annotations

import io
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.auth.dependencies import ControlledTester

from .provider import (
    CropIdentificationProvider,
    CropIdentificationProviderError,
    get_crop_identification_provider,
)
from .schemas import CropIdentificationResponse
from .service import InvalidGeminiCropResponseError, parse_crop_identification

router = APIRouter(prefix="/crop-identification", tags=["crop-identification"])
MAX_IMAGE_BYTES = 12_000_000
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

def get_configured_provider() -> CropIdentificationProvider:
    try:
        return get_crop_identification_provider()
    except CropIdentificationProviderError as exc:
        raise HTTPException(
            503, detail={"code": "GEMINI_CONFIGURATION_MISSING"}
        ) from exc


ProviderDep = Annotated[CropIdentificationProvider, Depends(get_configured_provider)]


async def _validated_image(upload: UploadFile) -> tuple[bytes, str]:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, detail={"code": "IMAGE_FORMAT_UNSUPPORTED"})
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, detail={"code": "IMAGE_SIZE_INVALID"})
    if not data:
        raise HTTPException(422, detail={"code": "CORRUPT_OR_INVALID_IMAGE"})
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        require_safe_image(image)
    except UnsafeImageError as exc:
        raise HTTPException(422, detail={"code": exc.reason_code}) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            422, detail={"code": "CORRUPT_OR_INVALID_IMAGE"}
        ) from exc
    return data, upload.content_type


@router.get("/health")
async def health() -> dict:
    try:
        provider = get_crop_identification_provider()
        del provider
        configured = True
    except CropIdentificationProviderError:
        configured = False
    return {
        "status": "internal_testing" if configured else "unavailable",
        "provider": "gemini",
        "general_farmer_release_authorized": False,
    }


@router.post("", response_model=CropIdentificationResponse)
async def identify_crop(
    tester: ControlledTester,
    provider: ProviderDep,
    image: UploadFile = File(...),
) -> CropIdentificationResponse:
    del tester
    data, mime_type = await _validated_image(image)
    try:
        raw = await provider.identify(data, mime_type)
        return parse_crop_identification(raw)
    except InvalidGeminiCropResponseError as exc:
        raise HTTPException(
            502, detail={"code": "INVALID_GEMINI_RESPONSE"}
        ) from exc
    except CropIdentificationProviderError as exc:
        code = str(exc)
        status = 503 if code == "GEMINI_CONFIGURATION_MISSING" else 502
        raise HTTPException(status, detail={"code": code}) from exc
