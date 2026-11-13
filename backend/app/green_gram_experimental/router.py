"""Authenticated Green Gram route; disabled until a model is approved."""

from __future__ import annotations

import io
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.modules.auth.constants import RoleName
from app.modules.auth.dependencies import TesterContext, require_any_role

from .service import GreenGramModelUnavailableError, GreenGramPredictionService, get_green_gram_prediction_service

router = APIRouter(prefix="/doctor/green-gram", tags=["green-gram-experimental"])
ALLOWED = frozenset({"image/jpeg", "image/png", "image/webp"})


async def require_green_gram_controlled_tester(
    tester: TesterContext = Depends(require_any_role(
        RoleName.INTERNAL_TESTER.value, RoleName.PILOT_TESTER.value, RoleName.KVK_REVIEWER.value
    )),
) -> TesterContext:
    return tester


@router.post("/predict")
async def predict_green_gram_disease(
    tester: Annotated[TesterContext, Depends(require_green_gram_controlled_tester)],
    image: UploadFile = File(...),
    service: GreenGramPredictionService = Depends(get_green_gram_prediction_service),
) -> dict:
    del tester
    if not settings.green_gram_experimental_enabled:
        await image.close()
        raise HTTPException(503, detail={
            "code": "GREEN_GRAM_MODEL_NOT_AVAILABLE",
            "message": "The Green Gram research model is disabled. It is available only in controlled testing.",
        })
    if image.content_type not in ALLOWED:
        await image.close()
        raise HTTPException(415, detail={"code": "GREEN_GRAM_IMAGE_FORMAT_UNSUPPORTED"})
    payload = await image.read(settings.green_gram_max_upload_bytes + 1)
    await image.close()
    if len(payload) > settings.green_gram_max_upload_bytes:
        raise HTTPException(413, detail={"code": "GREEN_GRAM_IMAGE_TOO_LARGE"})
    try:
        with Image.open(io.BytesIO(payload)) as opened:
            if opened.width * opened.height > settings.green_gram_max_image_pixels:
                raise HTTPException(422, detail={"code": "GREEN_GRAM_IMAGE_TOO_LARGE_DIMENSIONS"})
            if min(opened.width, opened.height) < settings.green_gram_min_image_dimension:
                raise HTTPException(422, detail={"code": "GREEN_GRAM_IMAGE_TOO_SMALL"})
            opened.load()
            decoded = opened.convert("RGB")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(422, detail={"code": "GREEN_GRAM_IMAGE_CORRUPTED"}) from exc
    try:
        return service.predict(decoded)
    except GreenGramModelUnavailableError as exc:
        raise HTTPException(503, detail={
            "code": str(exc), "message": "The Green Gram exploratory model is unavailable."
        }) from exc
