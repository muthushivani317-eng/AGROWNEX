"""ONNX Runtime implementation with fixed input/output names."""
from __future__ import annotations

from pathlib import Path

import numpy as np


class OnnxRuntime:
    backend = "onnx"

    def __init__(self, healthy_model: Path, disease_model: Path):
        self.paths = (healthy_model, disease_model)
        self._sessions: tuple[object, object] | None = None

    def load(self) -> None:
        import onnxruntime as ort

        providers = ["CPUExecutionProvider"]
        self._sessions = (
            ort.InferenceSession(str(self.paths[0]), providers=providers),
            ort.InferenceSession(str(self.paths[1]), providers=providers),
        )

    def _predict(self, index: int, batch: np.ndarray) -> np.ndarray:
        if self._sessions is None:
            self.load()
        assert self._sessions is not None
        return np.asarray(self._sessions[index].run(["logits"], {"image": batch})[0])

    def healthy_logits(self, batch: np.ndarray) -> np.ndarray:
        return self._predict(0, batch)

    def disease_logits(self, batch: np.ndarray) -> np.ndarray:
        return self._predict(1, batch)
