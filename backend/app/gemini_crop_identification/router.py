from __future__ import annotations

import io
import logging
import warnings
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.auth.dependencies import ControlledTester

from .confirmation import ConfirmationError, confirmation_store
from .provider import (
    CropIdentificationProvider,
    CropIdentificationProviderError,
    get_crop_identification_provider,
)
from .schemas import (
    CropConfirmationRequest,
    CropConfirmationResponse,
    CropIdentificationResponse,
    LocalizedText,
    PlantCheck,
    QualityChecks,
)
from .service import CROP_ID_VERSION, InvalidGeminiCropResponseError, parse_crop_identification

router = APIRouter(prefix="/crop-identification", tags=["crop-identification"])
logger = logging.getLogger("crop_identification")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
DISPLAY_NAMES = {
    "banana": "Banana",
    "paddy": "Paddy",
    "cotton": "Cotton",
    "groundnut": "Groundnut",
    "redgram": "Redgram",
    "chilli": "Chilli",
}
TA_REVIEW = "HUMAN_TRANSLATION_REVIEW_REQUIRED"


def get_configured_provider() -> CropIdentificationProvider:
    try:
        return get_crop_identification_provider()
    except CropIdentificationProviderError as exc:
        raise HTTPException(503, detail={"code": "GEMINI_CONFIGURATION_MISSING"}) from exc


ProviderDep = Annotated[CropIdentificationProvider, Depends(get_configured_provider)]


async def _validated_image(upload: UploadFile) -> tuple[bytes, str, QualityChecks]:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, detail={"code": "INVALID_IMAGE_FORMAT"})
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if not data:
        raise HTTPException(422, detail={"code": "CORRUPT_IMAGE"})
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, detail={"code": "IMAGE_TOO_LARGE"})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(data))
            if image.format != ALLOWED_TYPES[upload.content_type]:
                raise HTTPException(415, detail={"code": "INVALID_IMAGE_FORMAT"})
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise HTTPException(413, detail={"code": "IMAGE_TOO_LARGE"})
            image.load()
        require_safe_image(image)
    except HTTPException:
        raise
    except UnsafeImageError as exc:
        mapping = {
            "EXTREME_DARKNESS": "IMAGE_TOO_DARK",
            "EXTREME_BRIGHTNESS": "IMAGE_OVEREXPOSED",
            "INSUFFICIENT_DETAIL": "IMAGE_TOO_BLURRY",
        }
        raise HTTPException(
            422, detail={"code": mapping.get(exc.reason_code, exc.reason_code)}
        ) from exc
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(413, detail={"code": "IMAGE_TOO_LARGE"}) from None
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(422, detail={"code": "IMAGE_DECODE_FAILED"}) from exc
    return (
        data,
        upload.content_type,
        QualityChecks(passed=True, width=image.width, height=image.height, byte_size=len(data)),
    )


@router.get("/health")
async def health() -> dict:
    try:
        get_crop_identification_provider()
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
    data, mime_type, quality = await _validated_image(image)
    actor_id = str(tester.user.id)
    try:
        parsed = parse_crop_identification(await provider.identify(data, mime_type))
    except InvalidGeminiCropResponseError as exc:
        raise HTTPException(502, detail={"code": "INVALID_GEMINI_RESPONSE"}) from exc
    except CropIdentificationProviderError as exc:
        code = str(exc)
        raise HTTPException(
            503
            if code in {"GEMINI_CONFIGURATION_MISSING", "GEMINI_RATE_LIMITED", "GEMINI_TIMEOUT"}
            else 502,
            detail={"code": code},
        ) from exc
    record = confirmation_store.create(
        actor_id=actor_id, image=data, identified_crop=parsed.crop_id
    )
    identified = parsed.status == "identified"
    logger.info(
        "crop_identification_completed request_id=%s actor_hash_recorded=true status=%s",
        record.request_id,
        parsed.status,
    )
    return CropIdentificationResponse(
        request_id=record.request_id,
        status=parsed.status,
        identified_crop=parsed.crop_id,
        display_name=LocalizedText(
            en=DISPLAY_NAMES.get(parsed.crop_id or "", "") or "Not identified", ta=TA_REVIEW
        ),
        confidence=parsed.confidence,
        confidence_source="gemini_self_report" if parsed.confidence_available else "unavailable",
        reason_code=parsed.reason_code,
        reason_message=LocalizedText(
            en="Crop identified; farmer confirmation is required."
            if identified
            else (
                "Crop identity was not reliable. Retake the photo or use the "
                "controlled correction flow."
            ),
            ta=TA_REVIEW,
        ),
        provider_model=provider.model_name,
        crop_id_version=CROP_ID_VERSION,
        quality_checks=quality,
        plant_check=PlantCheck(
            outcome=parsed.plant_outcome, method="temporary_gemini_provider_assisted"
        ),
        created_at=record.created_at,
    )


@router.post("/confirm", response_model=CropConfirmationResponse)
async def confirm_crop(
    payload: CropConfirmationRequest, tester: ControlledTester
) -> CropConfirmationResponse:
    try:
        record = confirmation_store.confirm(
            actor_id=str(tester.user.id),
            request_id=payload.request_id,
            confirmed_crop=payload.confirmed_crop,
            correction=payload.decision == "farmer_selected_after_rejection",
        )
    except ConfirmationError as exc:
        raise HTTPException(422, detail={"code": str(exc)}) from exc
    assert record.confirmation_token is not None
    confirmed_at = datetime.now(UTC)
    return CropConfirmationResponse(
        request_id=record.request_id,
        confirmed_crop=payload.confirmed_crop,
        crop_source="farmer_selected_after_rejection"
        if payload.decision == "farmer_selected_after_rejection"
        else "gemini_confirmed",
        confirmation_token=record.confirmation_token,
        confirmed_at=confirmed_at,
        expires_at=record.expires_at,
    )
