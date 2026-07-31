"""Load-once, CPU-only, concurrency-safe frozen MobileNetV3 runtime."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

from .artifacts import ArtifactVerificationError, verify_artifacts
from .constants import (
    CLASS_TO_INDEX,
    CONFIDENCE_THRESHOLD,
    IMAGE_SIZE,
    INDEX_TO_CLASS,
    MARGIN_THRESHOLD,
    MODEL_NAME,
    MODEL_VERSION,
    TEMPERATURE,
)
from .errors import ModelUnavailableError
from .image import decode_image

logger = get_logger("disease.ml_runtime")


@dataclass(frozen=True)
class Prediction:
    raw_logits: list[float]
    top3: list[dict[str, float | str]]
    predicted_class: str
    confidence: float
    second_best_confidence: float
    accepted: bool
    preprocessing_ms: float
    inference_ms: float


class FrozenModelRuntime:
    def __init__(self, artifact_dir: Path | None = None) -> None:
        self.artifact_dir = artifact_dir or Path(settings.disease_model_artifact_dir)
        self._lock = threading.RLock()
        self._model: Any = None
        self._transform: Any = None
        self._verified = False
        self._error_category: str | None = None

    @property
    def ready(self) -> bool:
        return self._model is not None and self._verified

    @property
    def error_category(self) -> str | None:
        return self._error_category

    def load(self) -> None:
        with self._lock:
            if self.ready:
                return
            try:
                verify_artifacts(self.artifact_dir)
                import torch
                from torch import nn
                from torchvision import transforms
                from torchvision.models import mobilenet_v3_small
                from torchvision.transforms import InterpolationMode

                model = mobilenet_v3_small(weights=None)
                model.classifier[3] = nn.Linear(
                    model.classifier[3].in_features, len(CLASS_TO_INDEX)
                )
                checkpoint = torch.load(
                    self.artifact_dir / "best.pt", map_location="cpu", weights_only=True
                )
                if not isinstance(checkpoint, dict):
                    raise ArtifactVerificationError("checkpoint is not a wrapped dictionary")
                state = next(
                    (
                        checkpoint[key]
                        for key in ("model", "model_state_dict", "state_dict")
                        if key in checkpoint
                    ),
                    None,
                )
                if not isinstance(state, dict):
                    raise ArtifactVerificationError(
                        "checkpoint contains no supported state dictionary key"
                    )
                classes = checkpoint.get("classes")
                if classes is not None and classes != list(CLASS_TO_INDEX):
                    raise ArtifactVerificationError(
                        "checkpoint class order differs from class mapping"
                    )
                checkpoint_mapping = checkpoint.get("class_to_index")
                if checkpoint_mapping is not None and checkpoint_mapping != CLASS_TO_INDEX:
                    raise ArtifactVerificationError(
                        "checkpoint class mapping differs from frozen mapping"
                    )
                if (
                    checkpoint.get("model_name", MODEL_NAME) != MODEL_NAME
                    or checkpoint.get("image_size", IMAGE_SIZE) != IMAGE_SIZE
                ):
                    raise ArtifactVerificationError(
                        "checkpoint architecture metadata differs from frozen runtime"
                    )
                model.load_state_dict(state, strict=True)
                model.to("cpu")
                model.eval()
                self._transform = transforms.Compose(
                    [
                        transforms.Resize(
                            (IMAGE_SIZE, IMAGE_SIZE),
                            interpolation=InterpolationMode.BILINEAR,
                            antialias=True,
                        ),
                        transforms.ToTensor(),
                        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
                    ]
                )
                self._model = model
                self._verified = True
                self._error_category = None
                logger.info(
                    "Frozen disease model loaded and verified (version=%s device=cpu)",
                    MODEL_VERSION,
                )
            except Exception as exc:
                self._model = None
                self._transform = None
                self._verified = False
                self._error_category = type(exc).__name__
                logger.error(
                    "Frozen disease model startup failed (category=%s)", self._error_category
                )
                raise ModelUnavailableError() from exc

    def predict(self, image_base64: str, mime_type: str) -> Prediction:
        self.load()
        import torch

        started = time.perf_counter()
        decoded = decode_image(image_base64, mime_type)
        tensor = self._transform(decoded.image).unsqueeze(0)
        pre_ms = (time.perf_counter() - started) * 1000
        infer_started = time.perf_counter()
        with self._lock, torch.inference_mode():
            logits_tensor = self._model(tensor)[0]
        infer_ms = (time.perf_counter() - infer_started) * 1000
        logits = [float(value) for value in logits_tensor.tolist()]
        probabilities = torch.softmax(logits_tensor / TEMPERATURE, dim=0)
        values, indices = torch.topk(probabilities, k=3)
        top3 = [
            {"class_name": INDEX_TO_CLASS[int(index)], "score": float(score)}
            for score, index in zip(values, indices, strict=True)
        ]
        top1, top2 = float(values[0]), float(values[1])
        return Prediction(
            raw_logits=logits,
            top3=top3,
            predicted_class=str(top3[0]["class_name"]),
            confidence=top1,
            second_best_confidence=top2,
            accepted=top1 >= CONFIDENCE_THRESHOLD and (top1 - top2) >= MARGIN_THRESHOLD,
            preprocessing_ms=pre_ms,
            inference_ms=infer_ms,
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "model_family": "MobileNetV3 Small",
            "model_version": MODEL_VERSION,
            "supported_crops": list(("rice", "cotton", "groundnut")),
            "supported_classes": list(CLASS_TO_INDEX),
            "threshold": CONFIDENCE_THRESHOLD,
            "temperature": TEMPERATURE,
            "runtime_status": "ready" if self.ready else "unavailable",
            "artifact_verification_status": "verified" if self._verified else "not_verified",
            "official_accuracy_claim": False,
        }


_runtime = FrozenModelRuntime()


def get_model_runtime() -> FrozenModelRuntime:
    return _runtime
