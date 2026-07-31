"""Shared model-independent contracts for crop diagnosis providers.

Banana V3 remains implemented by ``app.banana_v3``. These contracts do not
change its preprocessing, calibration, thresholds, or decision engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class DiagnosisAvailability(StrEnum):
    AVAILABLE = "AVAILABLE_FIELD_VALIDATION_IN_PROGRESS"
    MODEL_NOT_AVAILABLE = "MODEL_NOT_AVAILABLE"


@dataclass(frozen=True)
class CropModelDescriptor:
    crop_id: str
    availability: DiagnosisAvailability
    model_version: str | None = None
    health_route: str | None = None
    prediction_route: str | None = None
    user_crop_confirmation_required: bool = True
    trained_crop_confirmation_gate: bool = False


@dataclass(frozen=True)
class ModelNotAvailable:
    status: DiagnosisAvailability
    crop_id: str
    code: str = "MODEL_NOT_AVAILABLE"
    diagnostic_result: None = None


class CropDiagnosisProvider(Protocol):
    descriptor: CropModelDescriptor

    def predict(self, image_bytes: bytes) -> object: ...


class UnavailableCropDiagnosisProvider:
    """Typed placeholder that never fabricates or forwards a diagnosis."""

    def __init__(self, crop_id: str) -> None:
        self.descriptor = CropModelDescriptor(
            crop_id=crop_id,
            availability=DiagnosisAvailability.MODEL_NOT_AVAILABLE,
        )

    def predict(self, image_bytes: bytes) -> ModelNotAvailable:
        del image_bytes
        return ModelNotAvailable(
            status=DiagnosisAvailability.MODEL_NOT_AVAILABLE,
            crop_id=self.descriptor.crop_id,
        )


PENDING_PROVIDERS = {
    crop: UnavailableCropDiagnosisProvider(crop)
    for crop in ("chilli", "redgram")
}
