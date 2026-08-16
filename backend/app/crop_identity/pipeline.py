"""Model-independent crop-ID gate and disease-dispatch safety policy.

This service is deliberately not attached to a farmer endpoint until an
enforced internal/pilot authorization role exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image

from .artifacts import CropIdentityArtifactError
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
    quality_passed: bool,
    plant_gate_passed: bool,
    runtime: CropIdentityRuntime,
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
    try:
        prediction = runtime.predict(image)
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
    # Disease routing always requires a separate farmer confirmation.
    return CropIdentityGateResult("CROP_MATCH", False, None, metadata)
