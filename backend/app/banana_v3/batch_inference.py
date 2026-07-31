"""Order-preserving batch inference with per-item fault isolation."""
from __future__ import annotations

from collections.abc import Sequence

from .inference_service import InferenceService
from .schemas import PredictionResponse


def predict_batch(
    service: InferenceService, inputs: Sequence[bytes], batch_size: int = 16
) -> list[PredictionResponse]:
    if not 1 <= batch_size <= 128:
        raise ValueError("batch_size must be between 1 and 128")
    results: list[PredictionResponse] = []
    for start in range(0, len(inputs), batch_size):
        results.extend(service.predict(item) for item in inputs[start : start + batch_size])
    return results
