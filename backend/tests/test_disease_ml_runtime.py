from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path

import pytest
from app.modules.disease.ml_runtime import artifacts
from app.modules.disease.ml_runtime.artifacts import ArtifactVerificationError
from app.modules.disease.ml_runtime.constants import (
    CLASS_TO_INDEX,
    CONFIDENCE_THRESHOLD,
    MARGIN_THRESHOLD,
    TEMPERATURE,
)
from app.modules.disease.ml_runtime.errors import InvalidDiseaseImageError
from app.modules.disease.ml_runtime.image import decode_image
from app.modules.disease.ml_runtime.orchestrator import decide
from app.modules.disease.ml_runtime.runtime import FrozenModelRuntime, Prediction
from PIL import Image


def _encoded(mode: str = "RGB", image_format: str = "PNG") -> str:
    image = Image.new(mode, (12, 8), 128)
    stream = io.BytesIO()
    image.save(stream, image_format)
    return base64.b64encode(stream.getvalue()).decode()


def _prediction(class_name: str = "rice_blast", confidence: float = 0.91) -> Prediction:
    return Prediction(
        raw_logits=[0.0] * 9,
        top3=[
            {"class_name": class_name, "score": confidence},
            {"class_name": "rice_tungro", "score": 0.05},
            {"class_name": "rice_brown_leaf_spot", "score": 0.04},
        ],
        predicted_class=class_name,
        confidence=confidence,
        second_best_confidence=0.05,
        accepted=confidence >= CONFIDENCE_THRESHOLD,
        preprocessing_ms=1.0,
        inference_ms=2.0,
    )


def _decide(prediction: Prediction, **overrides):
    values = {
        "request_id": "request-1",
        "selected_crop": "rice",
        "language": "ta",
        "prediction": prediction,
        "symptoms": [],
        "growth_stage": None,
        "knowledge_evidence": [],
        "image_reference": "local-ref",
        "image_storage_consent": False,
    }
    values.update(overrides)
    return decide(**values)


def test_frozen_tuning_values_are_unchanged():
    assert (TEMPERATURE, CONFIDENCE_THRESHOLD, MARGIN_THRESHOLD) == (
        1.1593322394366143,
        0.80,
        0.00,
    )


def test_artifact_verification_passes_and_detects_changes(tmp_path, monkeypatch):
    mapping = json.dumps(CLASS_TO_INDEX).encode()
    files = {
        "best.pt": b"checkpoint",
        "class_to_index.json": mapping,
        "v1_split_manifest.json": b"manifest-not-read-as-json",
        "runtime_training_config_snapshot.json": b"snapshot",
    }
    expected = {}
    for name, content in files.items():
        (tmp_path / name).write_bytes(content)
        expected[name] = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(artifacts, "EXPECTED_HASHES", expected)
    assert artifacts.verify_artifacts(tmp_path) == expected
    (tmp_path / "best.pt").write_bytes(b"altered")
    with pytest.raises(ArtifactVerificationError, match="hash mismatch"):
        artifacts.verify_artifacts(tmp_path)


def test_artifact_verification_rejects_missing_and_wrong_class_map(tmp_path, monkeypatch):
    mapping = json.dumps({"wrong": 0}).encode()
    files = {
        "best.pt": b"checkpoint",
        "class_to_index.json": mapping,
        "v1_split_manifest.json": b"manifest",
        "runtime_training_config_snapshot.json": b"snapshot",
    }
    expected = {}
    for name, content in files.items():
        (tmp_path / name).write_bytes(content)
        expected[name] = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(artifacts, "EXPECTED_HASHES", expected)
    with pytest.raises(ArtifactVerificationError, match="class mapping"):
        artifacts.verify_artifacts(tmp_path)
    (tmp_path / "best.pt").unlink()
    with pytest.raises(ArtifactVerificationError, match="missing"):
        artifacts.verify_artifacts(tmp_path)


@pytest.mark.parametrize("mode", ["RGB", "L", "RGBA"])
def test_image_decode_converts_supported_modes_to_rgb(mode):
    decoded = decode_image(_encoded(mode), "image/png")
    assert decoded.image.mode == "RGB"
    assert decoded.image.size == (12, 8)


def test_image_decode_rejects_invalid_base64_corrupt_and_unsupported_mime():
    with pytest.raises(InvalidDiseaseImageError):
        decode_image("not-base64", "image/jpeg")
    corrupt = base64.b64encode(b"not-an-image").decode()
    with pytest.raises(InvalidDiseaseImageError):
        decode_image(corrupt, "image/jpeg")
    with pytest.raises(InvalidDiseaseImageError):
        decode_image(_encoded(), "image/gif")


def test_image_decode_normalizes_exif_orientation():
    stream = io.BytesIO()
    image = Image.new("RGB", (12, 8), "green")
    exif = image.getexif()
    exif[274] = 6
    image.save(stream, "JPEG", exif=exif)
    decoded = decode_image(base64.b64encode(stream.getvalue()).decode(), "image/jpeg")
    assert decoded.image.size == (8, 12)


def test_image_decode_enforces_pixel_limit(monkeypatch):
    from app.modules.disease.ml_runtime import image as image_module

    monkeypatch.setattr(image_module.settings, "disease_max_image_pixels", 50)
    with pytest.raises(InvalidDiseaseImageError):
        decode_image(_encoded(), "image/png")


def test_real_runtime_loads_once_on_cpu_and_applies_frozen_math():
    artifact_dir = os.environ.get("DISEASE_MODEL_ARTIFACT_DIR")
    if not artifact_dir:
        pytest.skip("Frozen artifact directory is not configured for this test run.")
    import torch
    from torchvision.transforms import InterpolationMode

    runtime = FrozenModelRuntime(Path(artifact_dir))
    runtime.load()
    loaded_model = runtime._model
    runtime.load()
    assert runtime._model is loaded_model
    assert runtime._model.training is False
    assert next(runtime._model.parameters()).device.type == "cpu"
    resize = runtime._transform.transforms[0]
    assert resize.size == (224, 224)
    assert resize.interpolation == InterpolationMode.BILINEAR
    assert resize.antialias is True
    prediction = runtime.predict(_encoded(), "image/png")
    assert len(prediction.raw_logits) == 9
    probabilities = torch.softmax(torch.tensor(prediction.raw_logits) / TEMPERATURE, dim=0)
    assert float(probabilities.sum()) == pytest.approx(1.0, abs=1e-6)
    ordered = torch.topk(probabilities, 3).values.tolist()
    assert [item["score"] for item in prediction.top3] == pytest.approx(ordered)
    assert prediction.confidence == pytest.approx(ordered[0])


@pytest.mark.parametrize(
    ("prediction", "kwargs", "expected"),
    [
        (_prediction(confidence=0.79), {}, "ABSTAIN_LOW_CONFIDENCE"),
        (_prediction(), {"selected_crop": "cotton"}, "CROP_MISMATCH"),
        (_prediction(), {"selected_crop": "banana"}, "UNSUPPORTED_CROP"),
        (_prediction("paddy_healthy"), {}, "HEALTHY_LIKELY"),
        (
            _prediction(),
            {
                "symptoms": ["a"],
                "knowledge_evidence": [
                    {
                        "supports_class": "rice_blast",
                        "matched_symptoms": ["a"],
                        "conflicting_symptoms": [],
                        "verified": True,
                    }
                ],
            },
            "LIKELY_DIAGNOSIS",
        ),
        (
            _prediction(),
            {
                "symptoms": ["x"],
                "knowledge_evidence": [
                    {
                        "supports_class": "rice_blast",
                        "matched_symptoms": [],
                        "conflicting_symptoms": ["x"],
                        "verified": True,
                    }
                ],
            },
            "EXPERT_REVIEW_REQUIRED",
        ),
        (_prediction(), {}, "NEEDS_MORE_INFORMATION"),
    ],
)
def test_existing_orchestrator_decision_behaviour(prediction, kwargs, expected):
    result = _decide(prediction, **kwargs)
    assert result["decision_type"] == expected
    assert result["official_accuracy_claim"] is False
    assert "confirmed disease" not in json.dumps(result).lower()
    assert result["management_note"]["en"] == "Verify against official source."


def test_consent_controls_only_reference_persistence_not_inference_input():
    denied = _decide(_prediction(), image_storage_consent=False)
    allowed = _decide(_prediction(), image_storage_consent=True)
    assert denied["audit_record"]["image_reference"] is None
    assert allowed["audit_record"]["image_reference"] == "local-ref"
