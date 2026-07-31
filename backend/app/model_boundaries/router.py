"""Authenticated, upload-safe, fail-closed model boundaries.

No runtime is wired here until a verified artifact bundle passes the normal
release-readiness gates. These routes must never fabricate predictions.
"""
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.modules.auth.dependencies import CurrentUser

router = APIRouter(tags=["future-model-boundaries"])
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMAGE_BYTES = 12_000_000


async def _validate_image(image: UploadFile) -> None:
    if image.content_type not in _ALLOWED_TYPES:
        raise HTTPException(415, detail={"code": "IMAGE_FORMAT_UNSUPPORTED"})
    payload = await image.read(_MAX_IMAGE_BYTES + 1)
    await image.close()
    if not payload or len(payload) > _MAX_IMAGE_BYTES:
        raise HTTPException(413, detail={"code": "IMAGE_SIZE_INVALID"})


@router.get("/disease/crop-identification/health")
async def crop_identification_health():
    return {"status": "not_ready", "code": "CROP_IDENTIFICATION_MODEL_NOT_AVAILABLE"}


@router.post("/disease/crop-identification/predict")
async def identify_crop(current_user: CurrentUser, image: UploadFile = File(...)):
    del current_user
    await _validate_image(image)
    raise HTTPException(
        503, detail={"code": "CROP_IDENTIFICATION_MODEL_NOT_AVAILABLE"}
    )


@router.get("/plant-identifier/health")
async def plant_identifier_health():
    return {"status": "not_ready", "code": "PLANT_IDENTIFIER_MODEL_NOT_AVAILABLE"}


@router.post("/plant-identifier/predict")
async def identify_plant(current_user: CurrentUser, image: UploadFile = File(...)):
    del current_user
    await _validate_image(image)
    raise HTTPException(503, detail={"code": "PLANT_IDENTIFIER_MODEL_NOT_AVAILABLE"})


@router.get("/disease/verified-knowledge/{crop_id}/{disease_class_id}")
async def verified_disease_knowledge(
    crop_id: str, disease_class_id: str, current_user: CurrentUser
):
    del crop_id, disease_class_id, current_user
    # No production mapping is returned until every factual field has exact
    # document, printed-page and PDF-index evidence.
    raise HTTPException(404, detail={"code": "VERIFIED_DISEASE_KNOWLEDGE_NOT_AVAILABLE"})
