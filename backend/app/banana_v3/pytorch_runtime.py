"""Lazy, CPU-safe PyTorch runtime for frozen MobileNetV3 Small checkpoints."""
from __future__ import annotations

from pathlib import Path

import numpy as np


class PyTorchRuntime:
    backend = "pytorch"

    def __init__(self, healthy_checkpoint: Path, disease_checkpoint: Path):
        self.paths = (healthy_checkpoint, disease_checkpoint)
        self._models: tuple[object, object] | None = None

    @staticmethod
    def _load(path: Path, classes: int):
        import torch
        from torch import nn
        from torchvision.models import mobilenet_v3_small

        model = mobilenet_v3_small(weights=None)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, classes)
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        state = checkpoint
        if isinstance(checkpoint, dict):
            for key in ("model_state_dict", "state_dict", "model"):
                if key in checkpoint:
                    state = checkpoint[key]
                    break
        model.load_state_dict(state)
        return model.eval()

    def load(self) -> None:
        self._models = (self._load(self.paths[0], 2), self._load(self.paths[1], 3))

    def _predict(self, index: int, batch: np.ndarray) -> np.ndarray:
        if self._models is None:
            self.load()
        import torch

        assert self._models is not None
        with torch.inference_mode():
            return self._models[index](torch.from_numpy(batch)).cpu().numpy()

    def healthy_logits(self, batch: np.ndarray) -> np.ndarray:
        return self._predict(0, batch)

    def disease_logits(self, batch: np.ndarray) -> np.ndarray:
        return self._predict(1, batch)
