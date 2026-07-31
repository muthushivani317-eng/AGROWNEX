"""Lazy, CPU-safe inference for the frozen four-crop identity checkpoint."""
from __future__ import annotations

import math
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from .artifacts import (
    EXPECTED_CLASSES,
    CropIdentityArtifactError,
    verify_bundle,
)

ARTIFACT_ROOT = (
    Path(__file__).resolve().parents[2]
    / "model_artifacts"
    / "frozen_runtime"
    / "crop_identity_v1"
)


@dataclass(frozen=True)
class CropIdentityPrediction:
    model_name: str
    model_version: str
    checkpoint_sha256: str
    predicted_crop: str | None
    calibrated_probabilities: dict[str, float]
    confidence: float
    top_two_margin: float
    entropy: float
    applied_class_threshold: float
    fallback_threshold: float
    margin_threshold: float
    entropy_threshold: float
    accepted: bool
    reason_code: str
    field_validation_status: str
    official_accuracy_claim: bool
    general_farmer_inference_authorized: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CropIdentityRuntime:
    def __init__(self, artifact_root: Path = ARTIFACT_ROOT) -> None:
        self.root = artifact_root
        self._lock = threading.RLock()
        self._model: Any = None
        self._verified: dict[str, Any] | None = None

    @property
    def ready(self) -> bool:
        return (
            self._model is not None
            and self._verified is not None
            and not bool(getattr(self._model, "training", True))
        )

    def load(self) -> None:
        with self._lock:
            if self.ready:
                return
            verified = verify_bundle(self.root, inspect_checkpoint=True)
            try:
                import torch
                from torch import nn
                from torchvision.models import mobilenet_v3_small
            except ImportError as exc:
                raise CropIdentityArtifactError("PYTORCH_RUNTIME_UNAVAILABLE") from exc
            model = mobilenet_v3_small(weights=None)
            model.classifier[3] = nn.Linear(
                model.classifier[3].in_features, len(EXPECTED_CLASSES)
            )
            checkpoint = torch.load(
                self.root / "best.pt", map_location="cpu", weights_only=True
            )
            model.load_state_dict(checkpoint["model_state_dict"], strict=True)
            self._model = model.eval()
            self._verified = verified

    def _preprocess(self, image: Image.Image) -> np.ndarray:
        if self._verified is None:
            raise CropIdentityArtifactError("RUNTIME_NOT_LOADED")
        config = self._verified["preprocessing"]
        try:
            image = ImageOps.exif_transpose(image).convert("RGB")
            width, height = image.size
            scale = config["resize"] / min(width, height)
            image = image.resize(
                (round(width * scale), round(height * scale)),
                Image.Resampling.BILINEAR,
            )
            crop = config["center_crop"]
            left = (image.width - crop) // 2
            top = (image.height - crop) // 2
            image = image.crop((left, top, left + crop, top + crop))
            values = np.asarray(image, dtype=np.float32) / 255.0
            values = (
                values - np.asarray(config["mean"], dtype=np.float32)
            ) / np.asarray(config["std"], dtype=np.float32)
            return np.transpose(values, (2, 0, 1))[None, ...].astype(
                np.float32, copy=False
            )
        except (OSError, ValueError, TypeError) as exc:
            raise CropIdentityArtifactError(
                "CROP_IDENTITY_PREPROCESSING_FAILURE"
            ) from exc

    def predict(self, image: Image.Image, requested_crop: str) -> CropIdentityPrediction:
        if requested_crop not in EXPECTED_CLASSES:
            return self._decision(
                predicted_crop=None,
                probabilities={},
                confidence=0.0,
                margin=0.0,
                entropy=0.0,
                threshold=0.0,
                accepted=False,
                reason_code="UNSUPPORTED_REQUESTED_CROP",
            )
        self.load()
        assert self._verified is not None and self._model is not None
        import torch

        batch = torch.from_numpy(self._preprocess(image))
        with self._lock, torch.inference_mode():
            logits = self._model(batch).cpu()[0] / self._verified["temperature"]
        probabilities_tensor = torch.softmax(logits, dim=0)
        values = probabilities_tensor.tolist()
        order = sorted(range(len(values)), key=values.__getitem__, reverse=True)
        predicted = EXPECTED_CLASSES[order[0]]
        confidence = float(values[order[0]])
        margin = confidence - float(values[order[1]])
        entropy = -sum(value * math.log(max(value, 1e-12)) for value in values)
        threshold = self._verified["class_thresholds"].get(
            predicted, self._verified["fallback_threshold"]
        )
        passes_policy = (
            confidence >= threshold
            and margin >= self._verified["margin_threshold"]
            and entropy <= self._verified["entropy_threshold"]
        )
        accepted = passes_policy and predicted == requested_crop
        return self._decision(
            predicted_crop=predicted,
            probabilities=dict(zip(EXPECTED_CLASSES, values, strict=True)),
            confidence=confidence,
            margin=margin,
            entropy=entropy,
            threshold=threshold,
            accepted=accepted,
            reason_code="CROP_MATCH" if accepted else "CROP_IDENTITY_UNCERTAIN",
        )

    def _decision(
        self,
        *,
        predicted_crop: str | None,
        probabilities: dict[str, float],
        confidence: float,
        margin: float,
        entropy: float,
        threshold: float,
        accepted: bool,
        reason_code: str,
    ) -> CropIdentityPrediction:
        verified = self._verified or {}
        return CropIdentityPrediction(
            model_name=str(verified.get("model_name", "crop_identity_mobilenetv3_small_v1")),
            model_version=str(verified.get("model_version", "v1")),
            checkpoint_sha256=str(verified.get("checkpoint_sha256", "")),
            predicted_crop=predicted_crop,
            calibrated_probabilities=probabilities,
            confidence=confidence,
            top_two_margin=margin,
            entropy=entropy,
            applied_class_threshold=threshold,
            fallback_threshold=float(verified.get("fallback_threshold", 0.5)),
            margin_threshold=float(verified.get("margin_threshold", 1.0)),
            entropy_threshold=float(verified.get("entropy_threshold", 2.3740658328108566e-09)),
            accepted=accepted,
            reason_code=reason_code,
            field_validation_status=str(
                verified.get("field_validation_status", "PUBLIC_DATASET_PROVISIONAL")
            ),
            official_accuracy_claim=False,
            general_farmer_inference_authorized=False,
        )

    def health(self) -> dict[str, Any]:
        try:
            self.load()
            assert self._verified is not None
            return {
                "status": "ready",
                "model_name": self._verified["model_name"],
                "model_version": self._verified["model_version"],
                "checkpoint_sha256": self._verified["checkpoint_sha256"],
                "field_validation_status": "PUBLIC_DATASET_PROVISIONAL",
                "official_accuracy_claim": False,
                "general_farmer_inference_authorized": False,
            }
        except Exception as exc:
            return {
                "status": "not_ready",
                "error_category": type(exc).__name__,
                "official_accuracy_claim": False,
                "general_farmer_inference_authorized": False,
            }


_runtime = CropIdentityRuntime()


def get_crop_identity_runtime() -> CropIdentityRuntime:
    return _runtime
