"""Fail-closed single-image hierarchical inference orchestration."""
from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from .artifact_integrity import ArtifactIntegrityError, sha256_file, verify_artifacts
from .config import ARTIFACT_ROOT, LOG_ROOT, MODEL_VERSION, RUNTIME_PREFERENCE
from .decision_engine import accepted_code, disease_decision, healthy_decision
from .error_codes import DecisionCode
from .onnx_runtime import OnnxRuntime
from .prediction_logger import JsonlLogger
from .preprocessing import ImageValidationError, preprocess
from .pytorch_runtime import PyTorchRuntime
from .schemas import DiseaseBlock, GateBlock, PredictionResponse, ResultBlock, ResultStatus

DISPLAY_KEYS = {
    "banana__healthy": "banana.result.healthy",
    "banana__cordana_leaf_spot": "banana.result.cordana",
    "banana__pestalotiopsis_leaf_spot": "banana.result.pestalotiopsis",
    "banana__sigatoka_leaf_spot": "banana.result.sigatoka",
}


class InferenceService:
    def __init__(self, artifact_root: Path = ARTIFACT_ROOT, runtime=None):
        self.artifact_root = artifact_root
        self.runtime = runtime
        self.manifest: dict | None = None
        self.logger = JsonlLogger(LOG_ROOT / "predictions.jsonl")

    def load(self) -> None:
        self.manifest = verify_artifacts(self.artifact_root)
        if self.runtime is not None:
            return
        onnx = self.artifact_root / "onnx"
        checkpoints = self.artifact_root / "checkpoints"
        if RUNTIME_PREFERENCE in {"auto", "onnx"} and all(
            (onnx / name).is_file() for name in ("healthy_gate.onnx", "disease_classifier.onnx")
        ):
            self.runtime = OnnxRuntime(onnx / "healthy_gate.onnx", onnx / "disease_classifier.onnx")
        elif RUNTIME_PREFERENCE in {"auto", "pytorch"}:
            self.runtime = PyTorchRuntime(
                checkpoints / "healthy_gate_best.pt",
                checkpoints / "disease_classifier_best.pt",
            )
        else:
            raise ArtifactIntegrityError("configured runtime unavailable")
        self.runtime.load()

    def _error(self, request_id: uuid.UUID, code: DecisionCode, started: float) -> PredictionResponse:
        runtime = getattr(self.runtime, "backend", "pytorch")
        message = (
            "banana.error.unreadable_image"
            if code == DecisionCode.BV3_IMAGE_UNREADABLE
            else "banana.error.invalid_image"
            if code in {
                DecisionCode.BV3_IMAGE_FORMAT_UNSUPPORTED,
                DecisionCode.BV3_IMAGE_TOO_SMALL,
                DecisionCode.BV3_IMAGE_INVALID_CHANNELS,
                DecisionCode.BV3_OUT_OF_DOMAIN_IMAGE,
            }
            else "banana.error.runtime_failure"
        )
        return PredictionResponse(
            request_id=request_id,
            status=ResultStatus.error,
            decision_code=code.value,
            result=ResultBlock(confidence=0, margin=0),
            healthy_gate=GateBlock(confidence=0, margin=0, accepted=False),
            disease_classifier=DiseaseBlock(
                executed=False, confidence=0, margin=0, accepted=False
            ),
            message_key=message,
            requires_follow_up_photo=True,
            requires_human_review=True,
            runtime_backend=runtime,
            processing_time_ms=max(0, round((time.perf_counter() - started) * 1000)),
            timestamp_utc=datetime.now(UTC),
        )

    def predict(
        self,
        source: bytes | str | Path | Image.Image,
        *,
        request_id: uuid.UUID | None = None,
        consented_image_storage_reference: str | None = None,
    ) -> PredictionResponse:
        request_id = request_id or uuid.uuid4()
        started = time.perf_counter()
        try:
            if self.runtime is None:
                self.load()
            batch = preprocess(source)
            healthy = healthy_decision(self.runtime.healthy_logits(batch)[0])
            disease = None
            if not healthy.accepted:
                code = DecisionCode.BV3_HG_UNCERTAIN
                status, class_id, message = ResultStatus.uncertain, None, "banana.result.unable_to_confirm"
            elif healthy.predicted_class == "banana__healthy":
                code = DecisionCode.BV3_HEALTHY_ACCEPTED
                status, class_id, message = ResultStatus.accepted, healthy.predicted_class, DISPLAY_KEYS[healthy.predicted_class]
            else:
                disease = disease_decision(self.runtime.disease_logits(batch)[0])
                if disease.accepted:
                    code = accepted_code(disease.predicted_class)
                    status, class_id, message = ResultStatus.accepted, disease.predicted_class, DISPLAY_KEYS[disease.predicted_class]
                else:
                    code = DecisionCode.BV3_DC_UNCERTAIN
                    status, class_id, message = ResultStatus.uncertain, None, "banana.result.unable_to_confirm"
            chosen = disease or healthy
            response = PredictionResponse(
                request_id=request_id,
                status=status,
                decision_code=code.value,
                result=ResultBlock(
                    class_id=class_id,
                    display_name_key=DISPLAY_KEYS.get(class_id),
                    confidence=chosen.confidence,
                    margin=chosen.margin,
                ),
                healthy_gate=GateBlock(**healthy.__dict__),
                disease_classifier=DiseaseBlock(
                    executed=disease is not None,
                    predicted_class=disease.predicted_class if disease else None,
                    confidence=disease.confidence if disease else 0,
                    margin=disease.margin if disease else 0,
                    accepted=disease.accepted if disease else False,
                ),
                message_key=message,
                requires_follow_up_photo=status != ResultStatus.accepted,
                requires_human_review=status != ResultStatus.accepted,
                runtime_backend=self.runtime.backend,
                processing_time_ms=max(0, round((time.perf_counter() - started) * 1000)),
                timestamp_utc=datetime.now(UTC),
            )
        except ImageValidationError as exc:
            response = self._error(request_id, exc.code, started)
        except ArtifactIntegrityError:
            response = self._error(request_id, DecisionCode.BV3_ARTIFACT_INTEGRITY_FAILED, started)
        except Exception:
            response = self._error(request_id, DecisionCode.BV3_RUNTIME_ERROR, started)
        manifest_path = self.artifact_root / "manifests" / "artifact_manifest.json"
        self.logger.append({
            "request_id": response.request_id,
            "timestamp": response.timestamp_utc,
            "model_version": MODEL_VERSION,
            "artifact_manifest_hash": sha256_file(manifest_path) if manifest_path.is_file() else None,
            "runtime": response.runtime_backend,
            "decision_code": response.decision_code,
            "gate_confidence": response.healthy_gate.confidence,
            "gate_margin": response.healthy_gate.margin,
            "disease_confidence": response.disease_classifier.confidence,
            "disease_margin": response.disease_classifier.margin,
            "final_status": response.status,
            "processing_time_ms": response.processing_time_ms,
            "consented_image_storage_reference": consented_image_storage_reference,
        })
        return response
