"""Health and controlled-tester boundary for the frozen crop-identity runtime."""
from __future__ import annotations

import hashlib
import io
import json
import time
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.logging import get_logger
from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.auth.dependencies import ControlledTester

from .pipeline import run_controlled_crop_identity_pipeline
from .runtime import get_crop_identity_runtime

router = APIRouter(prefix="/crop-identity", tags=["crop-identity"])
audit_logger = get_logger("crop_identity.pipeline")
MAX_IMAGE_BYTES = 12_000_000
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _serializable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return asdict(value)
    return value


def _disease_dispatchers() -> dict[str, Any]:
    def banana(image: Image.Image):
        from app.banana_v3.inference_service import InferenceService

        payload = io.BytesIO()
        image.convert("RGB").save(payload, format="PNG")
        return InferenceService().predict(payload.getvalue())

    def legacy(crop: str):
        def dispatch(image: Image.Image):
            from app.legacy_joint.runtime import get_legacy_joint_runtime

            canonical = "rice" if crop == "paddy" else crop
            return get_legacy_joint_runtime().predict(
                canonical, image, crop_confirmed=True
            )

        return dispatch

    return {
        "banana": banana,
        "paddy": legacy("paddy"),
        "cotton": legacy("cotton"),
        "groundnut": legacy("groundnut"),
    }


async def _decode_upload(upload: UploadFile) -> Image.Image:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, detail={"code": "IMAGE_FORMAT_UNSUPPORTED"})
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if not data:
        raise HTTPException(422, detail={"code": "CORRUPT_OR_INVALID_IMAGE"})
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, detail={"code": "IMAGE_SIZE_INVALID"})
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


@router.get("/health")
async def crop_identity_health() -> dict:
    """Expose integrity readiness without authorizing or running prediction."""
    return get_crop_identity_runtime().health()


@router.post("/predict-controlled")
async def predict_controlled(
    request: Request,
    tester: ControlledTester,
    image: UploadFile = File(...),
    requested_crop: str = Form(...),
) -> dict[str, Any]:
    """Run the full crop gate only for a server-authorized controlled tester."""
    started = time.perf_counter()
    decoded = await _decode_upload(image)
    result = run_controlled_crop_identity_pipeline(
        authenticated=True,
        controlled_test_authorized=True,
        image=decoded,
        requested_crop=requested_crop.strip().lower(),
        quality_passed=True,
        # No independent semantic plant detector is proven. This does not claim
        # non-plant rejection; crop-ID remains closed-set and may abstain.
        plant_gate_passed=True,
        runtime=get_crop_identity_runtime(),
        disease_dispatchers=_disease_dispatchers(),
    )
    subject = hashlib.sha256(str(tester.user.id).encode()).hexdigest()[:16]
    audit_logger.info(
        "controlled_inference_result %s",
        json.dumps(
            {
                "timestamp_utc": time.time(),
                "subject_hash": subject,
                "resolved_role": tester.role,
                "route": request.url.path,
                "authorization_outcome": "allowed",
                "reason_code": result.reason_code,
                "model_invocation_attempted": True,
                "crop_id_model_invoked": result.crop_identity is not None,
                "disease_model_invoked": result.disease_adapter_called,
                "requested_crop": requested_crop.strip().lower(),
                "request_id": getattr(request.state, "request_id", ""),
            },
            separators=(",", ":"),
        ),
    )
    crop_identity = dict(result.crop_identity or {})
    crop_identity.pop("checkpoint_sha256", None)
    return {
        "reason_code": result.reason_code,
        "resolved_role": tester.role,
        "crop_identity": crop_identity or None,
        "disease_adapter_called": result.disease_adapter_called,
        "disease_adapter_name": result.disease_adapter_name,
        "disease_result": _serializable(result.response),
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "official_accuracy_claim": False,
        "general_farmer_inference_authorized": False,
        "non_plant_rejection_proven": False,
    }
