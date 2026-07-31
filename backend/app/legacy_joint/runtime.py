"""Load-once ONNX runtime with crop restriction before calibration and softmax."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from .artifacts import LegacyJointArtifactError, verify_bundle

ARTIFACT_ROOT = (
    Path(__file__).resolve().parents[2]
    / "model_artifacts"
    / "legacy_joint_v1_crop_constrained"
)
CROP_FILES = {"rice": "paddy", "cotton": "cotton", "groundnut": "groundnut"}


@dataclass(frozen=True)
class JointPrediction:
    outcome: str
    crop_id: str
    class_id: str | None
    qualitative_confidence: str
    accepted: bool


class LegacyJointRuntime:
    def __init__(self, artifact_root: Path = ARTIFACT_ROOT) -> None:
        self.root = artifact_root
        self._lock = threading.RLock()
        self._session: Any = None
        self._verified: dict[str, Any] | None = None
        self._routing: dict[str, Any] = {}
        self._temperature: dict[str, float] = {}
        self._thresholds: dict[str, tuple[float, float]] = {}

    @property
    def ready(self) -> bool:
        return self._session is not None and self._verified is not None

    def load(self) -> None:
        with self._lock:
            if self.ready:
                return
            verified = verify_bundle(self.root)
            routing = json.loads(
                (self.root / "runtime/crop_routing_policy.json").read_text("utf-8")
            )
            if (
                routing.get("user_crop_confirmation_required") is not True
                or routing.get("restrict_logits_before_calibration_and_softmax") is not True
            ):
                raise LegacyJointArtifactError("CROP_ROUTING_POLICY_INVALID")
            for canonical, artifact_crop in CROP_FILES.items():
                temperature = json.loads(
                    (self.root / f"calibration/{artifact_crop}_temperature.json").read_text(
                        "utf-8"
                    )
                )
                policy = json.loads(
                    (self.root / f"thresholds/{artifact_crop}_abstention_policy.json").read_text(
                        "utf-8"
                    )
                )
                if (
                    temperature.get("crop") != artifact_crop
                    or temperature.get("improved_nll") is not True
                    or policy.get("crop") != artifact_crop
                    or policy.get("passes_gate") is not True
                ):
                    raise LegacyJointArtifactError(f"CROP_POLICY_INVALID:{canonical}")
                self._temperature[canonical] = float(temperature["temperature"])
                self._thresholds[canonical] = (
                    float(policy["confidence_threshold"]),
                    float(policy["margin_threshold"]),
                )
            import onnxruntime

            session = onnxruntime.InferenceSession(
                str(self.root / "onnx/model_opset17.onnx"),
                providers=["CPUExecutionProvider"],
            )
            if session.get_inputs()[0].shape[1:] != [3, 224, 224]:
                raise LegacyJointArtifactError("RUNTIME_INPUT_SHAPE_INVALID")
            if session.get_outputs()[0].shape[-1] != 9:
                raise LegacyJointArtifactError("RUNTIME_OUTPUT_SHAPE_INVALID")
            self._routing = routing["groups"]
            self._session = session
            self._verified = verified

    @staticmethod
    def _preprocess(image: Image.Image) -> np.ndarray:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image = image.resize((224, 224), resample=Image.Resampling.BILINEAR)
        values = np.asarray(image, dtype=np.float32) / 255.0
        values = (values - np.asarray([0.485, 0.456, 0.406], dtype=np.float32)) / np.asarray(
            [0.229, 0.224, 0.225], dtype=np.float32
        )
        return np.transpose(values, (2, 0, 1))[None, ...]

    def predict(self, crop_id: str, image: Image.Image, *, crop_confirmed: bool) -> JointPrediction:
        if not crop_confirmed:
            raise ValueError("USER_CROP_CONFIRMATION_REQUIRED")
        if crop_id not in CROP_FILES:
            raise ValueError("UNSUPPORTED_CROP")
        self.load()
        artifact_crop = CROP_FILES[crop_id]
        group = self._routing[artifact_crop]
        indices = np.asarray(group["global_indices"], dtype=np.int64)
        with self._lock:
            assert self._session is not None
            input_name = self._session.get_inputs()[0].name
            raw = self._session.run(
                None, {input_name: self._preprocess(image)}
            )[0][0]
        # Security-critical ordering: restrict raw logits before temperature and softmax.
        local_logits = raw[indices] / self._temperature[crop_id]
        shifted = local_logits - local_logits.max()
        probs = np.exp(shifted) / np.exp(shifted).sum()
        order = np.argsort(probs)
        top_index = int(order[-1])
        confidence = float(probs[top_index])
        margin = confidence - float(probs[int(order[-2])])
        confidence_threshold, margin_threshold = self._thresholds[crop_id]
        accepted = confidence >= confidence_threshold and margin >= margin_threshold
        if not accepted:
            return JointPrediction("uncertain", crop_id, None, "low", False)
        class_id = str(group["class_ids"][top_index])
        if class_id not in group["class_ids"] or class_id in group["forbidden_class_ids"]:
            raise LegacyJointArtifactError("CROSS_CROP_CLASS_LEAK")
        qualitative = "high" if confidence >= 0.9 else "moderate"
        return JointPrediction("accepted", crop_id, class_id, qualitative, True)

    def health(self) -> dict[str, Any]:
        try:
            self.load()
            return {"status": "ready", "model_version": "legacy_joint_v1_crop_constrained"}
        except Exception as exc:
            return {"status": "not_ready", "error_category": type(exc).__name__}

    def version(self, crop_id: str) -> dict[str, Any]:
        self.load()
        artifact_crop = CROP_FILES[crop_id]
        confidence, margin = self._thresholds[crop_id]
        return {
            "model_version": "legacy_joint_v1_crop_constrained",
            "crop_id": crop_id,
            "class_ids": self._routing[artifact_crop]["class_ids"],
            "temperature": self._temperature[crop_id],
            "confidence_threshold": confidence,
            "margin_threshold": margin,
            "actual_onnx_opset": self._verified["actual_opset"],
            "parity_passed": self._verified["parity_passed"],
            "official_accuracy_claim": False,
            "field_validation_status": "IN_PROGRESS",
        }


_runtime = LegacyJointRuntime()


def get_legacy_joint_runtime() -> LegacyJointRuntime:
    return _runtime
