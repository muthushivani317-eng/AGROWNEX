"""Authenticated crop-specific routes backed by one verified nine-class runtime."""

from __future__ import annotations

import io
import json
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
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

from .field_test_override import (
    TEST_MODE_MARKER,
    legacy_joint_field_test_gate,
    legacy_joint_override_audit_logger,
)
from .runtime import (
    ARTIFACT_ROOT,
    get_legacy_joint_controlled_field_test_runtime,
    get_legacy_joint_runtime,
)

router = APIRouter(prefix="/disease", tags=["legacy-joint-crop-constrained"])
runtime = get_legacy_joint_runtime()
field_test_runtime = get_legacy_joint_controlled_field_test_runtime()
MAX_IMAGE_BYTES = 12_000_000
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
LOG_ROOT = ARTIFACT_ROOT / "logs"
logger = get_logger("legacy_joint.api")

require_legacy_joint_controlled_tester = require_crop_role("paddy")
LegacyJointControlledTester = Annotated[
    TesterContext, Depends(require_legacy_joint_controlled_tester)
]


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    outcome_helpful: bool
    corrected_class_id: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class FieldTestSessionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)


@router.post("/legacy-field-test/session/activate")
async def activate_field_test_session(
    payload: FieldTestSessionRequest, tester: LegacyJointControlledTester
) -> dict:
    try:
        legacy_joint_field_test_gate.activate(payload.session_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(403, detail={"code": str(exc)}) from exc
    legacy_joint_override_audit_logger.record(
        event="SESSION_ACTIVATED",
        session_id=payload.session_id,
        tester=tester,
    )
    return legacy_joint_field_test_gate.status()


@router.post("/legacy-field-test/session/deactivate")
async def deactivate_field_test_session(tester: LegacyJointControlledTester) -> dict:
    session_id = legacy_joint_field_test_gate.require_active()
    legacy_joint_override_audit_logger.record(
        event="SESSION_DEACTIVATED",
        session_id=session_id,
        tester=tester,
    )
    legacy_joint_field_test_gate.deactivate()
    return legacy_joint_field_test_gate.status()


@router.get("/legacy-field-test/session/status")
async def field_test_session_status(tester: LegacyJointControlledTester) -> dict:
    del tester
    return legacy_joint_field_test_gate.status()


async def _image(
    upload: UploadFile, requested_crop_id: str, actor_id: str, confirmation_token: str
) -> tuple[Image.Image, bytes, str]:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, detail={"code": "IMAGE_FORMAT_UNSUPPORTED"})
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, detail={"code": "IMAGE_SIZE_INVALID"})
    try:
        try:
            confirmation_store.validate(
                actor_id=actor_id,
                token=confirmation_token,
                crop="paddy" if requested_crop_id == "rice" else requested_crop_id,
                image=data,
            )
        except ConfirmationError as exc:
            raise HTTPException(422, detail={"code": str(exc)}) from exc
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
        return image, data, upload.content_type or "image/jpeg"
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(422, detail={"code": "IMAGE_DECODE_FAILED"}) from exc


def _crop_id(route_crop: str) -> str:
    return "rice" if route_crop == "paddy" else route_crop


for _route_crop in ("paddy", "cotton", "groundnut"):

    def _register(route_crop: Literal["paddy", "cotton", "groundnut"]):
        @router.post(f"/{route_crop}/predict")
        async def predict(
            tester: LegacyJointControlledTester,
            background_tasks: BackgroundTasks,
            image: UploadFile = File(...),
            crop_confirmed: bool = Form(...),
            crop_confirmation_token: str = Form(...),
            farm_id: uuid.UUID | None = Form(None),
            session: AsyncSession = Depends(get_session),
        ):
            try:
                session_id = legacy_joint_field_test_gate.require_active()
            except RuntimeError as exc:
                raise HTTPException(503, detail={"code": str(exc)}) from exc
            try:
                decoded, image_bytes, image_content_type = await _image(
                    image,
                    _crop_id(route_crop),
                    str(tester.user.id),
                    crop_confirmation_token,
                )
                result = field_test_runtime.predict(
                    _crop_id(route_crop),
                    decoded,
                    crop_confirmed=crop_confirmed,
                )
            except ValueError as exc:
                raise HTTPException(422, detail={"code": str(exc)}) from exc
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    503,
                    detail={
                        "code": classify_runtime_error(exc),
                        "message": "The disease model is not available.",
                    },
                ) from exc
            try:
                await persist_controlled_test_report(
                    session,
                    user_id=tester.user.id,
                    farm_id=farm_id,
                    image=image_bytes,
                    content_type=image_content_type,
                    capture_method="gallery",
                    crop=route_crop,
                    disease=result.class_id,
                    confidence=result.calibrated_confidence,
                    model_used="legacy_joint_v1_crop_constrained",
                    test_mode={
                        "active": True,
                        "code": "LEGACY_JOINT_CONTROLLED_FIELD_TEST_OVERRIDE",
                        "display_required": True,
                        "banner_text": TEST_MODE_MARKER,
                        "session_id": session_id,
                    },
                    outcome=result.outcome,
                )
            except Exception:
                logger.exception(
                    "controlled-test disease history persistence failed "
                    "(prediction still returned to farmer)"
                )
            field_test_logger.record(
                tester=tester,
                crop=route_crop,
                model_id="legacy_joint_v1_crop_constrained",
                predicted_class=result.class_id,
                confidence=result.calibrated_confidence,
                outcome=result.outcome,
            )
            legacy_joint_override_audit_logger.record(
                event="PREDICTION_SERVED",
                session_id=session_id,
                tester=tester,
                crop=route_crop,
                predicted_class=result.class_id,
                confidence=result.calibrated_confidence,
                outcome=result.outcome,
            )
            if tester.role == RoleName.KVK_REVIEWER.value:
                background_tasks.add_task(
                    run_shadow_comparison,
                    user_id=tester.user.id,
                    image=image_bytes,
                    content_type=image_content_type,
                    crop=route_crop,
                    local_model="legacy_joint_v1_crop_constrained",
                    local_status=result.outcome,
                    local_label=result.class_id,
                    local_confidence=result.calibrated_confidence,
                )
            return {
                "outcome": result.outcome,
                "crop_id": result.crop_id,
                "crop_identity_source": "user_confirmed_not_ai_verified",
                "class_id": result.class_id,
                "qualitative_confidence": result.qualitative_confidence,
                "calibrated_confidence": result.calibrated_confidence,
                "accepted": result.accepted,
                "official_accuracy_claim": False,
                "field_validation_status": "IN_PROGRESS",
                "test_mode": {
                    "active": True,
                    "code": "LEGACY_JOINT_CONTROLLED_FIELD_TEST_OVERRIDE",
                    "display_required": True,
                    "banner_text": TEST_MODE_MARKER,
                    "session_id": session_id,
                },
            }

        @router.post(f"/{route_crop}/feedback", status_code=202)
        async def feedback(payload: FeedbackRequest, tester: LegacyJointControlledTester):
            del tester
            LOG_ROOT.mkdir(parents=True, exist_ok=True)
            with (LOG_ROOT / f"{route_crop}_feedback.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload.model_dump(), ensure_ascii=False) + "\n")
            return {"accepted": True, "request_id": payload.request_id}

        @router.get(f"/{route_crop}/health")
        async def health():
            return runtime.health()

        @router.get(f"/{route_crop}/version")
        async def version():
            return runtime.version(_crop_id(route_crop))

    _register(_route_crop)
