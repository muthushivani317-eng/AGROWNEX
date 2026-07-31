from __future__ import annotations

import io
import math

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.auth.dependencies import ControlledTester

from .integrity import PACKAGES, RestrictedRuntimeIntegrityError
from .runtime import get_restricted_runtime

router = APIRouter(prefix="/disease", tags=["restricted-crop-runtime"])
MAX_IMAGE_BYTES = 12_000_000
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _image(upload: UploadFile) -> Image.Image:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, detail={"code": "IMAGE_FORMAT_UNSUPPORTED"})
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(422, detail={"code": "CORRUPT_OR_INVALID_IMAGE"})
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        require_safe_image(image)
        return image
    except UnsafeImageError as exc:
        raise HTTPException(422, detail={"code": exc.reason_code}) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            422, detail={"code": "CORRUPT_OR_INVALID_IMAGE"}
        ) from exc


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
        predicted is not None
        and predicted not in contract["classes"]
    ) or (
        confidence is not None and not math.isfinite(confidence)
    ) or (
        margin is not None and not math.isfinite(margin)
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
        tester: ControlledTester,
        image: UploadFile = File(...),
    ):
        del tester
        try:
            result = get_restricted_runtime(crop_id).predict(await _image(image))
            return normalized_response(crop_id, result)
        except HTTPException:
            raise
        except RestrictedRuntimeIntegrityError:
            return {
                "status": "runtime_error",
                "crop_id": crop_id,
                "runtime_id": PACKAGES[crop_id]["runtime_id"],
                "predicted_label": None,
                "confidence": None,
                "margin": None,
                "abstention_code": "MODEL_INTEGRITY_OR_RUNTIME_FAILURE",
                "restricted_runtime": True,
                "field_validated": False,
                "recommendation_available": False,
                "official_accuracy_claim": False,
            }
        except Exception:
            return {
                "status": "runtime_error",
                "crop_id": crop_id,
                "runtime_id": PACKAGES[crop_id]["runtime_id"],
                "predicted_label": None,
                "confidence": None,
                "margin": None,
                "abstention_code": "MODEL_INTEGRITY_OR_RUNTIME_FAILURE",
                "restricted_runtime": True,
                "field_validated": False,
                "recommendation_available": False,
                "official_accuracy_claim": False,
            }


for _crop_id in ("redgram", "chilli"):
    _register(_crop_id)
