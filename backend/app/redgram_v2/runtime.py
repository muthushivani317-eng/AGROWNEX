from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from torchvision.models import mobilenet_v3_small

from app.crop_runtime.registry import load_registry
from app.crop_runtime.resolver import RuntimeResolver


@dataclass(frozen=True)
class RedgramPrediction:
    outcome: str
    crop_id: str
    class_id: str | None
    qualitative_confidence: str
    accepted: bool


class RedgramRuntime:
    crop_id = "redgram"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._model: torch.nn.Module | None = None
        self._runtime = None

    def load(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            registry = load_registry()
            resolver = RuntimeResolver(registry, Path(__file__).resolve().parents[2])
            runtime = resolver.verify_integrity(self.crop_id)
            config = json.loads((runtime.root / "runtime_config.json").read_text("utf-8"))
            if config.get("architecture") != "mobilenet_v3_small":
                raise RuntimeError("REDGRAM_ARCHITECTURE_UNSUPPORTED")
            classes = [
                name for name, _ in sorted(runtime.class_to_index.items(), key=lambda item: item[1])
            ]
            model = mobilenet_v3_small(weights=None)
            model.classifier[3] = torch.nn.Linear(model.classifier[3].in_features, len(classes))
            checkpoint = torch.load(runtime.root / "best.pt", map_location="cpu", weights_only=True)
            if checkpoint.get("model_name") != config.get("model_name"):
                raise RuntimeError("REDGRAM_MODEL_NAME_MISMATCH")
            if checkpoint.get("classes") != classes:
                raise RuntimeError("REDGRAM_CLASS_ORDER_MISMATCH")
            model.load_state_dict(checkpoint["model"], strict=True)
            model.eval()
            self._model = model
            self._runtime = runtime

    def _preprocess(self, image: Image.Image) -> torch.Tensor:
        assert self._runtime is not None
        cfg = self._runtime.preprocessing
        image = ImageOps.exif_transpose(image).convert("RGB")
        resize = int(cfg["resize"])
        size = int(cfg["image_size"])
        scale = resize / min(image.size)
        image = image.resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.BILINEAR,
        )
        left = (image.width - size) // 2
        top = (image.height - size) // 2
        image = image.crop((left, top, left + size, top + size))
        values = np.asarray(image, dtype=np.float32) / 255.0
        values = (
            values - np.asarray(cfg["mean"], dtype=np.float32)
        ) / np.asarray(cfg["std"], dtype=np.float32)
        return torch.from_numpy(np.transpose(values, (2, 0, 1))).unsqueeze(0)

    def predict(self, image: Image.Image) -> RedgramPrediction:
        self.load()
        assert self._model is not None and self._runtime is not None
        with self._lock, torch.inference_mode():
            logits = self._model(self._preprocess(image))[0]
        temperature = float(self._runtime.temperature["temperature"])
        probabilities = torch.softmax(logits / temperature, dim=0)
        order = torch.argsort(probabilities)
        top = int(order[-1])
        second = int(order[-2])
        confidence = float(probabilities[top])
        margin = confidence - float(probabilities[second])
        classes = [
            name
            for name, _ in sorted(
                self._runtime.class_to_index.items(), key=lambda item: item[1]
            )
        ]
        class_id = classes[top]
        gates = self._runtime.thresholds.get(
            "class_thresholds",
            self._runtime.thresholds.get("class_specific_gates"),
        )
        gate = gates[class_id]
        accepted = (
            confidence >= float(gate["confidence_threshold"])
            and margin >= float(gate["margin_threshold"])
        )
        if not accepted:
            return RedgramPrediction("uncertain", self.crop_id, None, "low", False)
        return RedgramPrediction(
            "accepted",
            self.crop_id,
            class_id,
            "high" if confidence >= 0.9 else "moderate",
            True,
        )


_runtime = RedgramRuntime()


def get_redgram_runtime() -> RedgramRuntime:
    return _runtime
