"""Fail-closed validation for the frozen legacy joint ONNX bundle."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_CLASSES = [
    "cotton_fusarium_wilt",
    "cotton_healthy",
    "cotton_verticillium_wilt",
    "groundnut_healthy",
    "groundnut_rust",
    "paddy_healthy",
    "rice_blast",
    "rice_brown_leaf_spot",
    "rice_tungro",
]
EXPECTED_ONNX_SHA256 = "71539e500482d26e987994a08d6b85919a5e7bee03d7fc7cdbdf2dde74a37dfa"


class LegacyJointArtifactError(RuntimeError):
    """The frozen bundle is missing or inconsistent."""


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
        raise LegacyJointArtifactError(f"ARTIFACT_JSON_INVALID:{path.name}") from exc
    if not isinstance(value, dict):
        raise LegacyJointArtifactError(f"ARTIFACT_OBJECT_REQUIRED:{path.name}")
    return value


def verify_bundle(root: Path) -> dict[str, Any]:
    required = [
        "runtime/class_mapping.json",
        "runtime/preprocessing.json",
        "runtime/crop_routing_policy.json",
        "calibration/paddy_temperature.json",
        "calibration/cotton_temperature.json",
        "calibration/groundnut_temperature.json",
        "thresholds/paddy_abstention_policy.json",
        "thresholds/cotton_abstention_policy.json",
        "thresholds/groundnut_abstention_policy.json",
        "onnx/model_opset17.onnx",
        "onnx/export_receipt.json",
        "onnx/parity_receipt.json",
        "bundle/artifact_manifest.json",
        "bundle/bundle_verification.json",
        "reports/crop_constrained_recalibration_decision.json",
    ]
    for relative in required:
        if not (root / relative).is_file():
            raise LegacyJointArtifactError(f"ARTIFACT_MISSING:{relative}")

    manifest = _json(root / "bundle/artifact_manifest.json")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 17:
        raise LegacyJointArtifactError("ARTIFACT_MANIFEST_INVALID")
    hashes: dict[str, str] = {}
    for row in artifacts:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            raise LegacyJointArtifactError("ARTIFACT_MANIFEST_ROW_INVALID")
        path = root / row["path"]
        if not path.is_file():
            raise LegacyJointArtifactError(f"ARTIFACT_MISSING:{row['path']}")
        actual = sha256_file(path)
        if actual != row.get("sha256"):
            raise LegacyJointArtifactError(f"ARTIFACT_HASH_MISMATCH:{row['path']}")
        hashes[row["path"]] = actual

    if _json(root / "bundle/bundle_verification.json").get("verified") is not True:
        raise LegacyJointArtifactError("BUNDLE_VERIFICATION_NOT_PASSED")
    decision = _json(root / "reports/crop_constrained_recalibration_decision.json")
    if decision.get("decision") != "READY_FOR_BACKEND_INTEGRATION":
        raise LegacyJointArtifactError("INTEGRATION_DECISION_NOT_READY")
    if decision.get("crop_policies_ready") != {
        "paddy": True,
        "cotton": True,
        "groundnut": True,
    }:
        raise LegacyJointArtifactError("CROP_POLICIES_NOT_READY")

    export = _json(root / "onnx/export_receipt.json")
    parity = _json(root / "onnx/parity_receipt.json")
    onnx_path = root / "onnx/model_opset17.onnx"
    if sha256_file(onnx_path) != EXPECTED_ONNX_SHA256:
        raise LegacyJointArtifactError("ONNX_HASH_MISMATCH")
    if export.get("onnx_sha256") != EXPECTED_ONNX_SHA256:
        raise LegacyJointArtifactError("ONNX_RECEIPT_HASH_MISMATCH")
    if export.get("actual_opset") != 17 or parity.get("actual_opset") != 17:
        raise LegacyJointArtifactError("ONNX_OPSET_NOT_17")
    if parity.get("passed") is not True:
        raise LegacyJointArtifactError("ONNX_PARITY_NOT_PASSED")
    if parity.get("input_shape") != ["batch", 3, 224, 224]:
        raise LegacyJointArtifactError("ONNX_INPUT_SHAPE_INVALID")
    if parity.get("output_shape") != ["batch", 9]:
        raise LegacyJointArtifactError("ONNX_OUTPUT_SHAPE_INVALID")

    mapping = _json(root / "runtime/class_mapping.json")
    if mapping.get("ordered_classes") != EXPECTED_CLASSES:
        raise LegacyJointArtifactError("CLASS_ORDER_MISMATCH")
    if mapping.get("class_to_index") != {
        name: index for index, name in enumerate(EXPECTED_CLASSES)
    }:
        raise LegacyJointArtifactError("CLASS_MAPPING_MISMATCH")

    preprocessing = _json(root / "runtime/preprocessing.json")
    inference = preprocessing.get("inference", {})
    resize = inference.get("resize", {})
    normalization = inference.get("normalization", {})
    if not (
        preprocessing.get("decision") == "PREPROCESSING_PROVEN"
        and inference.get("image_size") == 224
        and inference.get("color_mode") == "RGB"
        and inference.get("exif_transpose") is True
        and resize.get("size") == [224, 224]
        and resize.get("crop") is None
        and resize.get("effective_interpolation") == "InterpolationMode.BILINEAR"
        and inference.get("tensor_conversion") == "torchvision.transforms.ToTensor"
        and normalization.get("mean") == [0.485, 0.456, 0.406]
        and normalization.get("std") == [0.229, 0.224, 0.225]
    ):
        raise LegacyJointArtifactError("PREPROCESSING_MISMATCH")

    import onnx

    graph = onnx.load(str(onnx_path), load_external_data=False)
    actual_opsets = {item.domain or "ai.onnx": int(item.version) for item in graph.opset_import}
    if actual_opsets.get("ai.onnx") != 17:
        raise LegacyJointArtifactError("ONNX_GRAPH_OPSET_NOT_17")

    return {
        "hashes": hashes,
        "onnx_sha256": EXPECTED_ONNX_SHA256,
        "actual_opset": 17,
        "parity_passed": True,
        "classes": EXPECTED_CLASSES,
        "preprocessing": preprocessing,
        "decision": decision["decision"],
    }
