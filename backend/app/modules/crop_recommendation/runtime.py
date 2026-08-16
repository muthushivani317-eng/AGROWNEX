from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import onnxruntime as ort

from .schemas import CropRecommendationRequest, RankedCrop

ARTIFACT_DIR = (
    Path(__file__).resolve().parents[3]
    / "model_artifacts"
    / "controlled_crop_recommendation_v1"
)


class CropRecommendationRuntimeError(RuntimeError):
    pass


class CropRecommendationRuntime:
    def __init__(self, artifact_dir: Path = ARTIFACT_DIR) -> None:
        self.artifact_dir = artifact_dir
        self.metadata = json.loads((artifact_dir / "metadata.json").read_text("utf-8"))
        sums = json.loads((artifact_dir / "SHA256SUMS.json").read_text("utf-8"))
        for name, expected in sums.items():
            actual = hashlib.sha256((artifact_dir / name).read_bytes()).hexdigest()
            if actual != expected:
                raise CropRecommendationRuntimeError("CROP_RECOMMENDATION_INTEGRITY_FAILED")
        if self.metadata.get("general_farmer_release_authorized") is not False:
            raise CropRecommendationRuntimeError("CONTROLLED_ONLY_POLICY_INVALID")
        self.classes = list(self.metadata["classes"])
        self.session = ort.InferenceSession(
            str(artifact_dir / "model.onnx"), providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name

    def predict(
        self, request: CropRecommendationRequest
    ) -> tuple[RankedCrop, list[RankedCrop]]:
        values = np.asarray(
            [[
                request.nitrogen,
                request.phosphorus,
                request.potassium,
                request.temperature_c,
                request.humidity_percent,
                request.ph,
                request.rainfall_mm,
            ]],
            dtype=np.float32,
        )
        outputs = self.session.run(None, {self.input_name: values})
        probabilities = np.asarray(outputs[1][0], dtype=np.float64)
        if probabilities.shape != (len(self.classes),) or not np.isfinite(probabilities).all():
            raise CropRecommendationRuntimeError("CROP_RECOMMENDATION_OUTPUT_INVALID")
        ranked_indices = np.argsort(probabilities)[::-1][:3]
        ranked = [
            RankedCrop(crop=self.classes[index], model_probability=float(probabilities[index]))
            for index in ranked_indices
        ]
        return ranked[0], ranked[1:]


@lru_cache(maxsize=1)
def get_runtime() -> CropRecommendationRuntime:
    return CropRecommendationRuntime()
