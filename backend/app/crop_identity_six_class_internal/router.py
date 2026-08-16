from __future__ import annotations

import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.crop_id_safety.gates import (
    SafetyArtifactError,
    assess_quality,
    public_quality,
    verify_safety_artifact,
)
from app.field_testing import field_test_logger
from app.gemini_crop_identification.confirmation import (
    ConfirmationError,
    confirmation_store,
)
from app.modules.auth.dependencies import ControlledTester
from app.modules.disease.runtime_errors import classify_runtime_error

from .runtime import IntegrityError, runtime

router = APIRouter(prefix="/crop-identity-six-class-internal", tags=["crop-identity-internal"])


@router.get("/health")
async def health():
    return runtime.health()


@router.post("/predict")
async def predict(tester: ControlledTester, image: UploadFile = File(...)):
    data = await image.read(12_000_001)
    if not data or len(data) > 12_000_000:
        raise HTTPException(422, detail={"code": "INVALID_IMAGE"})
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise HTTPException(422, detail={"code": "INVALID_IMAGE"}) from e
    try:
        safety = verify_safety_artifact()
        quality = assess_quality(im, safety)
        if quality.outcome != "QUALITY_ACCEPTABLE":
            return {
                "status": "low_quality",
                "reason_code": "LOW_QUALITY",
                "quality": public_quality(quality),
                "farmer_confirmation_required": True,
                "scope": "INTERNAL_ONLY",
                "official_accuracy_claim": False,
                "general_farmer_release": "BLOCKED",
            }
        result = runtime.predict(im)
        field_test_logger.record(
            tester=tester,
            crop=str(result.get("identified_crop") or "unknown"),
            model_id="crop_id_six_class_internal_v1",
            predicted_class=result.get("identified_crop"),
            confidence=result.get("confidence"),
            outcome=str(result.get("status", "unknown")),
        )
        record = confirmation_store.create(
            actor_id=str(tester.user.id),
            image=data,
            identified_crop=result["identified_crop"],
        )
        return {
            **result,
            "request_id": record.request_id,
            "image_sha256": record.image_sha256,
            "expires_at": record.expires_at,
            "confirmation_token": record.suggestion_token,
            "quality": public_quality(quality),
            "display_name": _display_name(result.get("identified_crop")),
            "suggested_crop": result.get("identified_crop"),
            "suggested_crop_display_ta": _display_name(result.get("identified_crop"))["ta"],
        }
    except SafetyArtifactError as exc:
        raise HTTPException(
            503,
            detail={
                "code": classify_runtime_error(exc),
                "message": "The crop-identification safety gate is unavailable.",
            },
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            503,
            detail={
                "code": classify_runtime_error(exc),
                "message": "The crop-identification model is unavailable.",
            },
        ) from exc


def _blocked(
    reason: str,
    quality,
    plant: dict,
    ood: dict | None = None,
) -> dict:
    return {
        "status": "uncertain",
        "identified_crop": None,
        "confidence": None,
        "reason_code": reason,
        "quality": public_quality(quality),
        "plant_gate": {"outcome": plant["outcome"]},
        "ood_gate": ood,
        "farmer_confirmation_required": True,
        "scope": "INTERNAL_ONLY",
        "official_accuracy_claim": False,
        "general_farmer_release": "BLOCKED",
    }


@router.post("/confirm")
async def confirm(
    tester: ControlledTester,
    request_id: str = Form(...),
    confirmed_crop: str = Form(...),
    correction: bool = Form(False),
    confirmation_token: str | None = Form(None),
) -> dict:
    if confirmed_crop not in {"banana", "paddy", "cotton", "groundnut", "chilli", "redgram"}:
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
        # Do not publish a decorative disease-routing flag: downstream routes
        # authorize the confirmed receipt itself, while release scope remains
        # explicitly restricted by the fields below.
        "reason_code": "DISEASE_RUNTIME_RESTRICTED",
        "scope": "INTERNAL_ONLY",
        "general_farmer_release": "BLOCKED",
    }


def _display_name(crop: str | None) -> dict[str, str]:
    labels = {
        "banana": {"en": "Banana", "ta": "வாழை"},
        "paddy": {"en": "Paddy", "ta": "நெல்"},
        "cotton": {"en": "Cotton", "ta": "பருத்தி"},
        "groundnut": {"en": "Groundnut", "ta": "நிலக்கடலை"},
        "chilli": {"en": "Chilli", "ta": "மிளகாய்"},
        "redgram": {"en": "Redgram", "ta": "துவரை"},
    }
    return labels.get(crop, {"en": "Crop", "ta": "பயிர்"})
