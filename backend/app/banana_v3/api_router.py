"""Authenticated FastAPI boundary for Banana V3 inference and feedback."""

from __future__ import annotations

import time
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.logging import get_logger
from app.field_testing import field_test_logger
from app.gemini_crop_identification.confirmation import ConfirmationError, confirmation_store
from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.auth.constants import RoleName
from app.modules.auth.dependencies import CurrentUser, TesterContext, require_crop_role
from app.modules.disease.controlled_test_reports import persist_controlled_test_report
from app.modules.disease.runtime_errors import classify_runtime_error
from app.modules.disease_comparison.service import run_shadow_comparison

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
logger = get_logger("banana_v3.api")


async def require_banana_controlled_tester(
    tester: TesterContext = Depends(require_crop_role("banana")),
) -> TesterContext:
    """Named wrapper keeps the standard controlled-role boundary testable."""
    return tester


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
async def predict(
    background_tasks: BackgroundTasks,
    tester: TesterContext = Depends(require_banana_controlled_tester),
    image: UploadFile = File(...),
    crop_confirmation_token: str = Form(...),
    farm_id: uuid.UUID | None = Form(None),
    session: AsyncSession = Depends(get_session),
):
    payload = await _safe_upload(image)
    try:
        try:
            confirmation_store.validate(
                actor_id=str(tester.user.id),
                token=crop_confirmation_token,
                crop="banana",
                image=payload,
            )
        except ConfirmationError as exc:
            raise HTTPException(422, detail={"code": str(exc)}) from exc
        decoded = load_image(payload)
        require_safe_image(decoded)
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
    result = _service.predict(payload)
    if result.decision_code in {
        DecisionCode.BV3_ARTIFACT_INTEGRITY_FAILED.value,
        DecisionCode.BV3_RUNTIME_ERROR.value,
    }:
        failure = (
            ArtifactIntegrityError(result.decision_code)
            if result.decision_code == DecisionCode.BV3_ARTIFACT_INTEGRITY_FAILED.value
            else RuntimeError(result.decision_code)
        )
        raise HTTPException(
            503,
            detail={
                "code": classify_runtime_error(failure),
                "message": "The banana disease model is unavailable.",
            },
        )
    if tester.role == RoleName.KVK_REVIEWER.value and result.status.value in {
        "accepted",
        "uncertain",
    }:
        try:
            await persist_controlled_test_report(
                session,
                user_id=tester.user.id,
                farm_id=farm_id,
                image=payload,
                content_type=image.content_type or "image/jpeg",
                capture_method="gallery",
                crop="banana",
                disease=result.result.class_id,
                confidence=result.result.confidence,
                model_used=result.model_version,
                test_mode={
                    "active": True,
                    "code": "BANANA_V3_CONTROLLED_TEST",
                    "display_required": True,
                    "banner_text": (
                        "TEST MODE — NOT AUTHORIZED FOR GENERAL RELEASE — " "RESULT NOT VALIDATED"
                    ),
                },
                outcome=result.status.value,
            )
        except Exception:
            logger.exception(
                "controlled-test disease history persistence failed "
                "(prediction still returned to farmer)"
            )
    field_test_logger.record(
        tester=tester,
        crop="banana",
        model_id=MODEL_VERSION,
        predicted_class=result.result.class_id,
        confidence=result.result.confidence,
        outcome=result.status.value,
    )
    if result.status.value in {"accepted", "uncertain"}:
        background_tasks.add_task(
            run_shadow_comparison,
            user_id=tester.user.id,
            image=payload,
            content_type=image.content_type or "image/jpeg",
            crop="banana",
            local_model=result.model_version,
            local_status=result.status.value,
            local_label=result.result.class_id,
            local_confidence=result.result.confidence,
        )
    return result


@router.post("/predict-batch", response_model=BatchPredictionResponse)
async def predict_many(
    tester: TesterContext = Depends(require_banana_controlled_tester),
    images: list[UploadFile] = File(...),
    batch_size: int = Query(16, ge=1, le=128),
):
    if not 1 <= len(images) <= 100:
        raise HTTPException(status_code=422, detail={"code": "INVALID_BATCH_SIZE"})
    payloads = [await _safe_upload(image) for image in images]
    results = predict_batch(_service, payloads, batch_size)
    for result in results:
        field_test_logger.record(
            tester=tester,
            crop="banana",
            model_id=MODEL_VERSION,
            predicted_class=result.result.class_id,
            confidence=result.result.confidence,
            outcome=result.status.value,
        )
    return BatchPredictionResponse(results=results)


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
