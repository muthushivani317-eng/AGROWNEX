"""Authenticated FastAPI boundary for Banana V3 inference and feedback."""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.crop_runtime.crop_domain import (
    CropIdentityUncertainError,
    require_verified_crop_domain,
)
from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.auth.dependencies import CurrentUser

from .artifact_integrity import ArtifactIntegrityError, verify_artifacts
from .batch_inference import predict_batch
from .config import ALLOWED_CONTENT_TYPES, ARTIFACT_ROOT, LOG_ROOT, MAX_UPLOAD_BYTES, MODEL_VERSION
from .error_codes import DecisionCode
from .feedback_logger import FeedbackLogger
from .inference_service import InferenceService
from .model_lineage import get_model_lineage
from .preprocessing import ImageValidationError, load_image
from .schemas import BatchPredictionResponse, FeedbackRequest, PredictionResponse

router = APIRouter(prefix="/disease/banana", tags=["banana-v3"])
_service = InferenceService()
_feedback = FeedbackLogger(LOG_ROOT / "feedback.jsonl")


async def _safe_upload(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail={"code": "BV3_IMAGE_FORMAT_UNSUPPORTED"})
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if not data:
        raise HTTPException(
            status_code=422,
            detail={"code": DecisionCode.BV3_IMAGE_UNREADABLE.value},
        )
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail={"code": "BV3_IMAGE_FORMAT_UNSUPPORTED"})
    return data


@router.post("/predict", response_model=PredictionResponse)
async def predict(current_user: CurrentUser, image: UploadFile = File(...)):
    del current_user
    payload = await _safe_upload(image)
    try:
        decoded = load_image(payload)
        require_safe_image(decoded)
        require_verified_crop_domain(decoded, "banana")
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code.value},
        ) from exc
    except UnsafeImageError:
        return _service._error(
            uuid.uuid4(),
            DecisionCode.BV3_OUT_OF_DOMAIN_IMAGE,
            time.perf_counter(),
        )
    except CropIdentityUncertainError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.reason_code},
        ) from exc
    return _service.predict(payload)


@router.post("/predict-batch", response_model=BatchPredictionResponse)
async def predict_many(
    current_user: CurrentUser,
    images: list[UploadFile] = File(...),
    batch_size: int = Query(16, ge=1, le=128),
):
    del current_user
    if not 1 <= len(images) <= 100:
        raise HTTPException(status_code=422, detail={"code": "INVALID_BATCH_SIZE"})
    payloads = [await _safe_upload(image) for image in images]
    return BatchPredictionResponse(results=predict_batch(_service, payloads, batch_size))


@router.post("/feedback", status_code=202)
async def feedback(payload: FeedbackRequest, current_user: CurrentUser):
    del current_user
    _feedback.log(payload)
    return {"accepted": True, "request_id": str(payload.request_id)}


@router.get("/health")
async def health():
    try:
        manifest = verify_artifacts(ARTIFACT_ROOT)
        return {"status": "ready", "bundle_version": manifest["bundle_version"]}
    except ArtifactIntegrityError:
        return {"status": "not_ready", "code": "BV3_ARTIFACT_INTEGRITY_FAILED"}


@router.get("/version")
async def version():
    return {"model_version": MODEL_VERSION, "lineage": get_model_lineage()}
