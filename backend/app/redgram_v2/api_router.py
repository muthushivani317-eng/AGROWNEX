from __future__ import annotations

import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.admin.dependencies import AdminContextDep

from .runtime import get_redgram_runtime

# Superseded candidate adapter retained for authenticated diagnostic checks only.
# It is not mounted by the application API router and is not the deployed runtime.
router = APIRouter(prefix="/disease/redgram", tags=["redgram-v2-unvalidated-candidate"])
runtime = get_redgram_runtime()
MAX_IMAGE_BYTES = 12_000_000
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _image(upload: UploadFile) -> Image.Image:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, detail={"status": "invalid_image"})
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, detail={"status": "invalid_image"})
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        require_safe_image(image)
        return image
    except UnsafeImageError as exc:
        raise HTTPException(422, detail={"status": "out_of_domain"}) from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(422, detail={"status": "invalid_image"}) from exc


@router.post("/predict")
async def predict(admin: AdminContextDep, image: UploadFile = File(...)):
    del admin
    try:
        result = runtime.predict(await _image(image))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, detail={"status": "model_load_failed"}) from exc
    return {
        "outcome": result.outcome,
        "crop_id": result.crop_id,
        "crop_identity_source": "user_confirmed_not_ai_verified",
        "class_id": result.class_id,
        "qualitative_confidence": result.qualitative_confidence,
        "accepted": result.accepted,
        "official_accuracy_claim": False,
        "field_validation_status": "TN_FIELD_VALIDATION_PENDING",
    }


@router.get("/health")
async def health():
    try:
        runtime.load()
        return {
            "status": "unvalidated_candidate_not_deployed",
            "general_farmer_inference_authorized": False,
        }
    except Exception:
        return {"status": "not_ready"}
