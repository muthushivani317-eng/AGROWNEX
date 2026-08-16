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
from app.field_testing import field_test_logger
from app.image_safety import UnsafeImageError, require_safe_image
from app.gemini_crop_identification.confirmation import (
    ConfirmationError,
    confirmation_store,
)
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


async def _decode_upload(upload: UploadFile) -> tuple[Image.Image, bytes]:
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
        return image, data
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
) -> dict[str, Any]:
    """Run the full crop gate only for a server-authorized controlled tester."""
    started = time.perf_counter()
    decoded, image_bytes = await _decode_upload(image)
    result = run_controlled_crop_identity_pipeline(
        authenticated=True,
        controlled_test_authorized=True,
        image=decoded,
        quality_passed=True,
        # No independent semantic plant detector is proven. This does not claim
        # non-plant rejection; crop-ID remains closed-set and may abstain.
        plant_gate_passed=True,
        runtime=get_crop_identity_runtime(),
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
                "requested_crop": None,
                "request_id": getattr(request.state, "request_id", ""),
            },
            separators=(",", ":"),
        ),
    )
    crop_identity = dict(result.crop_identity or {})
    crop_identity.pop("checkpoint_sha256", None)
    identified_crop = crop_identity.get("predicted_crop")
    record = confirmation_store.create(
        actor_id=str(tester.user.id),
        image=image_bytes,
        identified_crop=identified_crop,
    )
    field_test_logger.record(
        tester=tester,
        crop=identified_crop or "unknown",
        model_id=str(crop_identity.get("model_name", "crop_identity_mobilenetv3_small_v1")),
        predicted_class=crop_identity.get("predicted_crop"),
        confidence=crop_identity.get("confidence"),
        outcome=result.reason_code,
    )
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
        "request_id": record.request_id,
        "image_sha256": record.image_sha256,
        "expires_at": record.expires_at,
        "confirmation_token": record.suggestion_token,
        "farmer_confirmation_required": True,
        "suggested_crop": identified_crop,
    }


@router.post("/confirm")
async def confirm_controlled(
    tester: ControlledTester,
    request_id: str = Form(...),
    confirmed_crop: str = Form(...),
    correction: bool = Form(False),
    confirmation_token: str | None = Form(None),
) -> dict[str, Any]:
    if confirmed_crop not in {"banana", "paddy", "cotton", "groundnut"}:
        raise HTTPException(422, detail={"code": "UNSUPPORTED_CROP"})
    try:
        record = confirmation_store.confirm(
            actor_id=str(tester.user.id),
            request_id=request_id,
            confirmed_crop=confirmed_crop,
            correction=correction,
            suggestion_token=confirmation_token,
        )
    except ConfirmationError as exc:
        raise HTTPException(409, detail={"code": str(exc)}) from exc
    return {
        "status": "FARMER_CORRECTED" if correction else "FARMER_CONFIRMED",
        "request_id": record.request_id,
        "confirmed_crop": record.confirmed_crop,
        "image_sha256": record.image_sha256,
        "expires_at": record.expires_at,
        "confirmation_token": record.confirmation_token,
        "farmer_confirmation_required": True,
        "disease_routing_authorized": True,
        "scope": "CONTROLLED_TESTING_ONLY",
        "general_farmer_release": "BLOCKED",
    }
