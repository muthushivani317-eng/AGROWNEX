"""Strict, fail-closed verification of the frozen crop-identity bundle."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_CHECKPOINT_SHA256 = (
    "7cf80d093267821024577275f7538766d03271d765fbe5f18798b1d9fc26ca81"
)
EXPECTED_MODEL_NAME = "crop_identity_mobilenetv3_small_v1"
EXPECTED_ARCHITECTURE = "mobilenet_v3_small"
EXPECTED_CLASSES = ["banana", "paddy", "cotton", "groundnut"]
EXPECTED_PREPROCESSING = {
    "resize": 256,
    "center_crop": 224,
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225],
}
REQUIRED_FILES = [
    "best.pt",
    "training_config.json",
    "preprocessing.json",
    "class_to_index.json",
    "index_to_class.json",
    "temperature.json",
    "selected_class_specific_thresholds.json",
    "abstention_policy.json",
    "TRAINING_RECEIPT.json",
    "DEV_EVALUATION.json",
    "CALIBRATION_REPORT.json",
    "PRE_TEST_FREEZE_RECORD.json",
    "PROVISIONAL_TEST_RECEIPT.json",
    "PROVISIONAL_TEST_RESULTS.json",
    "runtime_config.json",
    "SHA256SUMS.txt",
    "DEPLOYMENT_BUNDLE_SHA256SUMS.txt",
]


class CropIdentityArtifactError(RuntimeError):
    """The bundle is missing, modified, contradictory, or unsafe to load."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CropIdentityArtifactError(f"ARTIFACT_JSON_INVALID:{path.name}") from exc
    if not isinstance(value, dict):
        raise CropIdentityArtifactError(f"ARTIFACT_OBJECT_REQUIRED:{path.name}")
    return value


def _checksum_manifest(root: Path, name: str) -> dict[str, str]:
    path = root / name
    if not path.is_file():
        raise CropIdentityArtifactError(f"ARTIFACT_MISSING:{name}")
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise CropIdentityArtifactError(f"CHECKSUM_MANIFEST_INVALID:{name}")
        relative = parts[1].strip().lstrip("*").replace("\\", "/")
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise CropIdentityArtifactError(f"CHECKSUM_PATH_INVALID:{relative}")
        if relative in entries:
            raise CropIdentityArtifactError(f"CHECKSUM_DUPLICATE_PATH:{relative}")
        entries[relative] = parts[0].lower()
    if not entries:
        raise CropIdentityArtifactError(f"CHECKSUM_MANIFEST_EMPTY:{name}")
    return entries


def _verify_entries(root: Path, entries: dict[str, str], manifest: str) -> dict[str, str]:
    verified = {}
    for relative, expected in entries.items():
        path = root / relative
        if not path.is_file():
            raise CropIdentityArtifactError(f"ARTIFACT_MISSING:{relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise CropIdentityArtifactError(f"ARTIFACT_HASH_MISMATCH:{manifest}:{relative}")
        verified[relative] = actual
    return verified


def verify_bundle(root: Path, *, inspect_checkpoint: bool = False) -> dict[str, Any]:
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            raise CropIdentityArtifactError(f"ARTIFACT_MISSING:{relative}")
    inner = _checksum_manifest(root, "SHA256SUMS.txt")
    deployment = _checksum_manifest(root, "DEPLOYMENT_BUNDLE_SHA256SUMS.txt")
    inner_hashes = _verify_entries(root, inner, "SHA256SUMS.txt")
    deployment_hashes = _verify_entries(
        root, deployment, "DEPLOYMENT_BUNDLE_SHA256SUMS.txt"
    )
    for relative, digest in inner_hashes.items():
        if deployment_hashes.get(relative) != digest:
            raise CropIdentityArtifactError(f"CHECKSUM_MANIFEST_CONFLICT:{relative}")
    if sha256_file(root / "best.pt") != EXPECTED_CHECKPOINT_SHA256:
        raise CropIdentityArtifactError("CHECKPOINT_HASH_MISMATCH")

    runtime = _json(root / "runtime_config.json")
    if runtime.get("model_name") != EXPECTED_MODEL_NAME:
        raise CropIdentityArtifactError("MODEL_NAME_MISMATCH")
    if runtime.get("architecture") != EXPECTED_ARCHITECTURE:
        raise CropIdentityArtifactError("ARCHITECTURE_MISMATCH")
    if runtime.get("classes") != EXPECTED_CLASSES:
        raise CropIdentityArtifactError("CLASS_ORDER_MISMATCH")
    if runtime.get("field_validation_status") != "PUBLIC_DATASET_PROVISIONAL":
        raise CropIdentityArtifactError("FIELD_VALIDATION_STATUS_INVALID")
    if runtime.get("official_accuracy_claim") is not False:
        raise CropIdentityArtifactError("OFFICIAL_ACCURACY_CLAIM_INVALID")
    if runtime.get("general_farmer_inference_authorized") is not False:
        raise CropIdentityArtifactError("FARMER_AUTHORIZATION_INVALID")
    if runtime.get("non_plant_rejection_proven") is not False:
        raise CropIdentityArtifactError("NON_PLANT_CLAIM_INVALID")

    class_to_index = _json(root / "class_to_index.json")
    index_to_class = _json(root / "index_to_class.json")
    expected_mapping = {name: index for index, name in enumerate(EXPECTED_CLASSES)}
    if class_to_index != expected_mapping:
        raise CropIdentityArtifactError("CLASS_MAPPING_MISMATCH")
    if index_to_class != {str(index): name for name, index in expected_mapping.items()}:
        raise CropIdentityArtifactError("INDEX_MAPPING_MISMATCH")
    preprocessing = _json(root / "preprocessing.json")
    if preprocessing != EXPECTED_PREPROCESSING:
        raise CropIdentityArtifactError("PREPROCESSING_MISMATCH")

    temperature = _json(root / "temperature.json")
    value = temperature.get("temperature")
    if (
        temperature.get("method") != "temperature_scaling"
        or temperature.get("calibration_split") != "calibration"
        or not isinstance(value, int | float)
        or float(value) <= 0
    ):
        raise CropIdentityArtifactError("TEMPERATURE_CONFIG_INVALID")
    thresholds = _json(root / "selected_class_specific_thresholds.json")
    policy = _json(root / "abstention_policy.json")
    class_thresholds = thresholds.get("class_thresholds")
    if (
        thresholds.get("status") != "PUBLIC_DATASET_PROVISIONAL"
        or thresholds.get("selection_split") != "calibration"
        or thresholds.get("official_accuracy_claim") is not False
        or set(class_thresholds or {}) != set(EXPECTED_CLASSES)
    ):
        raise CropIdentityArtifactError("THRESHOLD_CONFIG_INVALID")
    if (
        policy.get("policy_version") != "crop_identity_abstention_v1"
        or policy.get("selection_split") != "calibration"
        or policy.get("class_thresholds") != class_thresholds
        or policy.get("fallback_threshold") != thresholds.get("fallback_threshold")
        or not isinstance(policy.get("margin_threshold"), int | float)
        or not isinstance(policy.get("entropy_threshold"), int | float)
        or policy.get("accepted_reason_code") != "CROP_MATCH"
        or policy.get("rejected_reason_code") != "CROP_IDENTITY_UNCERTAIN"
        or policy.get("non_plant_rejection_proven") is not False
        or policy.get("general_farmer_inference_authorized") is not False
    ):
        raise CropIdentityArtifactError("ABSTENTION_POLICY_INVALID")
    freeze = _json(root / "PRE_TEST_FREEZE_RECORD.json")
    if (
        freeze.get("status") != "PRE_TEST_CONFIGURATION_FROZEN"
        or freeze.get("checkpoint_epoch") != 2
        or freeze.get("post_test_tuning_authorized") is not False
        or freeze.get("official_accuracy_claim") is not False
    ):
        raise CropIdentityArtifactError("FREEZE_RECORD_INVALID")

    checkpoint_metadata = None
    if inspect_checkpoint:
        checkpoint_metadata = inspect_checkpoint_metadata(root / "best.pt")
    return {
        "model_name": EXPECTED_MODEL_NAME,
        "model_version": runtime.get("model_version"),
        "architecture": EXPECTED_ARCHITECTURE,
        "classes": EXPECTED_CLASSES,
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
        "preprocessing": preprocessing,
        "temperature": float(value),
        "class_thresholds": {key: float(value) for key, value in class_thresholds.items()},
        "fallback_threshold": float(policy["fallback_threshold"]),
        "margin_threshold": float(policy["margin_threshold"]),
        "entropy_threshold": float(policy["entropy_threshold"]),
        "field_validation_status": "PUBLIC_DATASET_PROVISIONAL",
        "official_accuracy_claim": False,
        "general_farmer_inference_authorized": False,
        "non_plant_rejection_proven": False,
        "inner_hashes": inner_hashes,
        "deployment_hashes": deployment_hashes,
        "checkpoint_metadata": checkpoint_metadata,
    }


def inspect_checkpoint_metadata(path: Path) -> dict[str, Any]:
    try:
        import torch
    except ImportError as exc:
        raise CropIdentityArtifactError("PYTORCH_RUNTIME_UNAVAILABLE") from exc
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict):
        raise CropIdentityArtifactError("CHECKPOINT_OBJECT_REQUIRED")
    if checkpoint.get("model_name") != EXPECTED_MODEL_NAME:
        raise CropIdentityArtifactError("CHECKPOINT_MODEL_NAME_MISMATCH")
    if checkpoint.get("architecture") != EXPECTED_ARCHITECTURE:
        raise CropIdentityArtifactError("CHECKPOINT_ARCHITECTURE_MISMATCH")
    if checkpoint.get("class_to_index") != {
        name: index for index, name in enumerate(EXPECTED_CLASSES)
    }:
        raise CropIdentityArtifactError("CHECKPOINT_CLASS_MAPPING_MISMATCH")
    if checkpoint.get("epoch") != 2:
        raise CropIdentityArtifactError("CHECKPOINT_EPOCH_MISMATCH")
    state = checkpoint.get("model_state_dict")
    if not isinstance(state, dict):
        raise CropIdentityArtifactError("CHECKPOINT_STATE_DICT_MISSING")
    weight = state.get("classifier.3.weight")
    bias = state.get("classifier.3.bias")
    if tuple(getattr(weight, "shape", ())) != (4, 1024) or tuple(
        getattr(bias, "shape", ())
    ) != (4,):
        raise CropIdentityArtifactError("CHECKPOINT_OUTPUT_DIMENSION_MISMATCH")
    return {
        "epoch": 2,
        "model_name": EXPECTED_MODEL_NAME,
        "architecture": EXPECTED_ARCHITECTURE,
        "class_to_index": checkpoint["class_to_index"],
        "classifier_weight_shape": [4, 1024],
        "classifier_bias_shape": [4],
        "state_dict_entries": len(state),
    }
