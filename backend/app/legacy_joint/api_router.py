"""Authenticated crop-specific routes backed by one verified nine-class runtime."""
from __future__ import annotations

import io
import json
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from app.crop_runtime.crop_domain import (
    CropIdentityUncertainError,
    require_verified_crop_domain,
)
from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.auth.dependencies import CurrentUser

from .runtime import ARTIFACT_ROOT, get_legacy_joint_runtime

router = APIRouter(prefix="/disease", tags=["legacy-joint-crop-constrained"])
runtime = get_legacy_joint_runtime()
MAX_IMAGE_BYTES = 12_000_000
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
LOG_ROOT = ARTIFACT_ROOT / "logs"


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    outcome_helpful: bool
    corrected_class_id: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


async def _image(upload: UploadFile, requested_crop_id: str) -> Image.Image:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, detail={"code": "IMAGE_FORMAT_UNSUPPORTED"})
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, detail={"code": "IMAGE_SIZE_INVALID"})
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        try:
            require_safe_image(image)
        except UnsafeImageError as exc:
            raise HTTPException(
                422,
                detail={
                    "code": "OUT_OF_DOMAIN_IMAGE",
                    "message": (
                        "The image could not be safely assessed. "
                        "Please upload a clear close-up crop photo."
                    ),
                },
            ) from exc
        try:
            require_verified_crop_domain(image, requested_crop_id)
        except CropIdentityUncertainError as exc:
            raise HTTPException(
                422,
                detail={"code": exc.reason_code},
            ) from exc
        return image
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(422, detail={"code": "IMAGE_DECODE_FAILED"}) from exc


def _crop_id(route_crop: str) -> str:
    return "rice" if route_crop == "paddy" else route_crop


for _route_crop in ("paddy", "cotton", "groundnut"):
    def _register(route_crop: Literal["paddy", "cotton", "groundnut"]):
        @router.post(f"/{route_crop}/predict")
        async def predict(
            current_user: CurrentUser,
            image: UploadFile = File(...),
            crop_confirmed: bool = Form(...),
        ):
            del current_user
            try:
                result = runtime.predict(
                    _crop_id(route_crop),
                    await _image(image, _crop_id(route_crop)),
                    crop_confirmed=crop_confirmed,
                )
            except ValueError as exc:
                raise HTTPException(422, detail={"code": str(exc)}) from exc
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(503, detail={"code": "MODEL_NOT_AVAILABLE"}) from exc
            return {
                "outcome": result.outcome,
                "crop_id": result.crop_id,
                "crop_identity_source": "user_confirmed_not_ai_verified",
                "class_id": result.class_id,
                "qualitative_confidence": result.qualitative_confidence,
                "accepted": result.accepted,
                "official_accuracy_claim": False,
                "field_validation_status": "IN_PROGRESS",
            }

        @router.post(f"/{route_crop}/feedback", status_code=202)
        async def feedback(payload: FeedbackRequest, current_user: CurrentUser):
            del current_user
            LOG_ROOT.mkdir(parents=True, exist_ok=True)
            with (LOG_ROOT / f"{route_crop}_feedback.jsonl").open(
                "a", encoding="utf-8"
            ) as handle:
                handle.write(json.dumps(payload.model_dump(), ensure_ascii=False) + "\n")
            return {"accepted": True, "request_id": payload.request_id}

        @router.get(f"/{route_crop}/health")
        async def health():
            return runtime.health()

        @router.get(f"/{route_crop}/version")
        async def version():
            return runtime.version(_crop_id(route_crop))

    _register(_route_crop)
