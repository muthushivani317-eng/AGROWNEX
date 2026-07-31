"""Model-independent crop-ID gate and disease-dispatch safety policy.

This service is deliberately not attached to a farmer endpoint until an
enforced internal/pilot authorization role exists.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PIL import Image

from .artifacts import EXPECTED_CLASSES, CropIdentityArtifactError
from .runtime import CropIdentityRuntime


@dataclass(frozen=True)
class CropIdentityGateResult:
    reason_code: str
    disease_adapter_called: bool
    disease_adapter_name: str | None
    crop_identity: dict[str, Any] | None
    response: Any = None


def run_controlled_crop_identity_pipeline(
    *,
    authenticated: bool,
    controlled_test_authorized: bool,
    image: Image.Image | None,
    requested_crop: str,
    quality_passed: bool,
    plant_gate_passed: bool,
    runtime: CropIdentityRuntime,
    disease_dispatchers: dict[str, Callable[[Image.Image], Any]],
) -> CropIdentityGateResult:
    if not authenticated:
        return CropIdentityGateResult("AUTHENTICATION_REQUIRED", False, None, None)
    if not controlled_test_authorized:
        return CropIdentityGateResult("INFERENCE_NOT_AUTHORIZED", False, None, None)
    if image is None:
        return CropIdentityGateResult("CORRUPT_OR_INVALID_IMAGE", False, None, None)
    if not quality_passed:
        return CropIdentityGateResult("LOW_QUALITY_IMAGE", False, None, None)
    if not plant_gate_passed:
        return CropIdentityGateResult("NON_PLANT_REJECTED", False, None, None)
    if requested_crop not in EXPECTED_CLASSES:
        return CropIdentityGateResult(
            "UNSUPPORTED_REQUESTED_CROP", False, None, None
        )
    try:
        prediction = runtime.predict(image, requested_crop)
    except CropIdentityArtifactError as exc:
        reason = (
            "CROP_IDENTITY_INTEGRITY_FAILURE"
            if "HASH" in str(exc) or "MISMATCH" in str(exc)
            else "CROP_IDENTITY_RUNTIME_UNAVAILABLE"
        )
        return CropIdentityGateResult(reason, False, None, None)
    metadata = prediction.as_dict()
    if not prediction.accepted:
        return CropIdentityGateResult(
            "CROP_IDENTITY_UNCERTAIN", False, None, metadata
        )
    if prediction.predicted_crop != requested_crop:
        return CropIdentityGateResult(
            "CROP_IDENTITY_UNCERTAIN", False, None, metadata
        )
    dispatcher = disease_dispatchers.get(requested_crop)
    if dispatcher is None:
        return CropIdentityGateResult(
            "DISEASE_RUNTIME_UNAVAILABLE", False, None, metadata
        )
    response = dispatcher(image)
    return CropIdentityGateResult(
        "CROP_MATCH", True, requested_crop, metadata, response
    )
