from __future__ import annotations

import io
import math
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.logging import get_logger
from app.field_testing import field_test_logger
from app.gemini_crop_identification.confirmation import ConfirmationError, confirmation_store
from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.auth.constants import RoleName
from app.modules.auth.dependencies import TesterContext, require_crop_role
from app.modules.disease.controlled_test_reports import persist_controlled_test_report
from app.modules.disease.runtime_errors import classify_runtime_error
from app.modules.disease_comparison.service import run_shadow_comparison

from .integrity import PACKAGES, RestrictedRuntimeIntegrityError
from .runtime import get_restricted_runtime

router = APIRouter(prefix="/disease", tags=["restricted-crop-runtime"])
MAX_IMAGE_BYTES = 12_000_000
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
TEST_MODE_MARKER = {
    "active": True,
    "code": "RESTRICTED_CROP_CONTROLLED_TEST",
    "display_required": True,
    "banner_text": "TEST MODE — NOT AUTHORIZED FOR GENERAL RELEASE — RESULT NOT VALIDATED",
}
logger = get_logger("restricted_crops.api")


async def _image(
    upload: UploadFile, *, actor_id: str, crop_id: str, token: str
) -> tuple[Image.Image, bytes, str]:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, detail={"code": "IMAGE_FORMAT_UNSUPPORTED"})
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(422, detail={"code": "CORRUPT_OR_INVALID_IMAGE"})
    try:
        try:
            confirmation_store.validate(
                actor_id=actor_id,
                token=token,
                crop=crop_id,
                image=data,
            )
        except ConfirmationError as exc:
            raise HTTPException(422, detail={"code": str(exc)}) from exc
        image = Image.open(io.BytesIO(data))
        image.load()
        require_safe_image(image)
        return image, data, upload.content_type or "image/jpeg"
    except UnsafeImageError as exc:
        raise HTTPException(422, detail={"code": exc.reason_code}) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(422, detail={"code": "CORRUPT_OR_INVALID_IMAGE"}) from exc


def normalized_response(crop_id: str, result) -> dict[str, object]:
    contract = PACKAGES[crop_id]
    status_map = {
        "ACCEPTED_RESTRICTED_RESULT": "accepted",
        "ABSTAINED": "abstained",
        "RUNTIME_ERROR": "runtime_error",
    }
    status = status_map.get(result.status, "runtime_error")
    predicted = result.predicted_class
    confidence = result.calibrated_confidence
    margin = result.calibrated_margin
    if (
        (predicted is not None and predicted not in contract["classes"])
        or (confidence is not None and not math.isfinite(confidence))
        or (margin is not None and not math.isfinite(margin))
    ):
        status = "runtime_error"
        predicted = None
        confidence = None
        margin = None
    if crop_id == "redgram" and predicted == "redgram__leaf_spot":
        status = "abstained"
        abstention_code = "REDGRAM_LEAF_SPOT_AUTOMATIC_ACCEPTANCE_DISABLED"
    else:
        abstention_code = result.abstention_code
    return {
        "status": status,
        "crop_id": crop_id,
        "runtime_id": contract["runtime_id"],
        "predicted_label": predicted,
        "confidence": confidence,
        "margin": margin,
        "abstention_code": (
            abstention_code
            if status == "abstained"
            else "MODEL_INTEGRITY_OR_RUNTIME_FAILURE"
            if status == "runtime_error"
            else None
        ),
        "restricted_runtime": True,
        "field_validated": False,
        "recommendation_available": False,
        "official_accuracy_claim": False,
        "test_mode": TEST_MODE_MARKER,
    }


def _register(crop_id: str) -> None:
    @router.get(f"/{crop_id}/restricted-health")
    async def health():
        try:
            get_restricted_runtime(crop_id).load()
            return {
                "crop_id": crop_id,
                "model_available": True,
                "runtime_mode": "restricted",
                "automatic_diagnosis_complete": crop_id == "chilli",
                "field_validated": False,
                "general_farmer_inference_authorized": False,
            }
        except Exception:
            return {
                "crop_id": crop_id,
                "model_available": False,
                "runtime_mode": "restricted",
                "automatic_diagnosis_complete": False,
                "field_validated": False,
                "general_farmer_inference_authorized": False,
            }

    @router.post(f"/{crop_id}/predict-restricted")
    async def predict(
        background_tasks: BackgroundTasks,
        tester: TesterContext = Depends(require_crop_role(crop_id)),
        image: UploadFile = File(...),
        crop_confirmation_token: str = Form(...),
        farm_id: uuid.UUID | None = Form(None),
        kvk_session: bool = Form(False),
        review_consent: bool | None = Form(None),
        session: AsyncSession = Depends(get_session),
    ):
        try:
            decoded, image_bytes, image_content_type = await _image(
                image,
                actor_id=str(tester.user.id),
                crop_id=crop_id,
                token=crop_confirmation_token,
            )
            result = get_restricted_runtime(crop_id).predict(decoded)
            response = normalized_response(crop_id, result)
            is_kvk_redgram = (
                crop_id == "redgram" and kvk_session and tester.role == RoleName.KVK_REVIEWER.value
            )
            if kvk_session and tester.role != RoleName.KVK_REVIEWER.value:
                raise HTTPException(403, detail={"code": "KVK_REVIEWER_REQUIRED"})
            should_persist = response["status"] == "accepted" or is_kvk_redgram
            if should_persist:
                try:
                    report = await persist_controlled_test_report(
                        session,
                        user_id=tester.user.id,
                        farm_id=farm_id,
                        image=image_bytes,
                        content_type=image_content_type,
                        capture_method="gallery",
                        crop=crop_id,
                        disease=response["predicted_label"],
                        confidence=response["confidence"],
                        model_used=str(PACKAGES[crop_id]["runtime_id"]),
                        test_mode=TEST_MODE_MARKER,
                        outcome=str(response["status"]),
                        retain_for_review=(bool(review_consent) if is_kvk_redgram else True),
                        kvk_session=is_kvk_redgram,
                    )
                    response["report_id"] = str(report.id)
                    response["review_status"] = report.review_status
                except Exception:
                    logger.exception(
                        "controlled-test disease history persistence failed "
                        "(prediction still returned to farmer)"
                    )
                    response["report_id"] = None
                    response["review_status"] = None
            response["kvk_session"] = is_kvk_redgram
            field_test_logger.record(
                tester=tester,
                crop=crop_id,
                model_id=str(PACKAGES[crop_id]["runtime_id"]),
                predicted_class=response["predicted_label"],
                confidence=response["confidence"],
                outcome=str(response["status"]),
            )
            if tester.role == RoleName.KVK_REVIEWER.value and response["status"] in {
                "accepted",
                "abstained",
            }:
                background_tasks.add_task(
                    run_shadow_comparison,
                    user_id=tester.user.id,
                    image=image_bytes,
                    content_type=image_content_type,
                    crop=crop_id,
                    local_model=str(PACKAGES[crop_id]["runtime_id"]),
                    local_status=str(response["status"]),
                    local_label=response["predicted_label"],
                    local_confidence=response["confidence"],
                )
            return response
        except HTTPException:
            raise
        except RestrictedRuntimeIntegrityError as exc:
            raise HTTPException(
                503,
                detail={
                    "code": classify_runtime_error(exc),
                    "message": "The disease model is not available.",
                },
            ) from exc
        except Exception as exc:
            raise HTTPException(
                503,
                detail={
                    "code": classify_runtime_error(exc),
                    "message": "The disease model is not available.",
                },
            ) from exc


for _crop_id in ("redgram", "chilli"):
    _register(_crop_id)
