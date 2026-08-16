"""Reconstruct the proven legacy joint runtime from fixed, pre-test evidence only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path("/content/drive/MyDrive/AgrowAI_V1")
INPUTS = {
    "checkpoint": ROOT / "outputs/mobilenetv3_small_v1/best.pt",
    "dev_logits": ROOT / "checkpoints/mobilenetv3_small_v1/baseline_exports/dev_logits.npz",
    "calibration_logits": ROOT / "checkpoints/mobilenetv3_small_v1/baseline_exports/calibration_logits.npz",
    "class_mapping": ROOT / "checkpoints/mobilenetv3_small_v1/baseline_exports/class_to_index.json",
    "split_manifest": ROOT / "outputs/v1_split_manifest.json",
    "runtime_snapshot": ROOT / "checkpoints/mobilenetv3_small_v1/runtime_training_config_snapshot.json",
}
EXPECTED_HASHES = {
    "checkpoint": "f9719d48d3a8d274d039f0bd36d78cc5fa1282a8f15b2f471ab27d5c043e8117",
    "dev_logits": "3a4943304816686b6721bc69f5c202d5705b3898e11cb648b3b2ad4471e6ce46",
    "calibration_logits": "d9981a2235a843be375d65e2b713225df6aad4e22870153f0a0ed4df8be77e9f",
    "class_mapping": "639d3615eb166f860221a2290ba87dabcca814ba74723315422e5a567388cc29",
    "split_manifest": "482cf5f9144cc0563e4e85d2bb3a9cb0e901896edf6bcae2d949dadfa65c232f",
    "runtime_snapshot": "018769fba169cbe3421d8d6adb9b4fb0af89f1029f2e37460c08cf2cec08ee46",
}
EXPECTED_CLASSES = [
    "cotton_fusarium_wilt", "cotton_healthy", "cotton_verticillium_wilt",
    "groundnut_healthy", "groundnut_rust", "paddy_healthy", "rice_blast",
    "rice_brown_leaf_spot", "rice_tungro",
]
CROP_CLASSES = {
    "cotton": EXPECTED_CLASSES[0:3],
    "groundnut": EXPECTED_CLASSES[3:5],
    "paddy": EXPECTED_CLASSES[5:9],
}
HISTORICAL_TEMPERATURE = 1.1593322394366143
CONFIDENCE_GRID = [round(0.50 + 0.05 * index, 2) for index in range(10)]
MARGIN_GRID = [round(0.05 * index, 2) for index in range(7)]
VALID_DECISIONS = {
    "READY_FOR_BACKEND_INTEGRATION",
    "REQUIRES_CROP_CONSTRAINED_RECALIBRATION",
    "REQUIRES_THRESHOLD_REVIEW",
    "REQUIRES_RETRAINING",
    "RECONSTRUCTION_FAILED",
}
PREPROCESSING_DECISIONS = {
    "PREPROCESSING_PROVEN",
    "PREPROCESSING_AMBIGUOUS",
    "PREPROCESSING_NOT_FOUND",
}
FROZEN_PREPROCESSING_EVIDENCE = {
    "decision": "PREPROCESSING_PROVEN",
    "inference": {
        "image_size": 224,
        "color_mode": "RGB",
        "exif_transpose": True,
        "resize": {
            "operation": "torchvision.transforms.Resize",
            "size": [224, 224],
            "crop": None,
            "interpolation_explicitly_specified": False,
            "effective_interpolation": "InterpolationMode.BILINEAR",
        },
        "tensor_conversion": "torchvision.transforms.ToTensor",
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
        },
    },
    "training_augmentation": {
        "runtime_inference": False,
        "operations": [
            "RandomResizedCrop(size, scale=(0.85, 1.0))",
            "RandomHorizontalFlip(0.5)",
            "RandomRotation(10)",
            "ColorJitter(0.15, 0.15, 0.10, 0.03)",
            "GaussianBlur(3, sigma=(0.1, 0.6))",
        ],
    },
    "evidence": [
        {
            "path": "D:/AgrowAI/knowledge_base/vision/src/data_pipeline.py",
            "sha256": "9af2fe7d0fe3ce358a22e19b071463000f078d4e960f464196509c1f4ceaa6cb",
            "lines": "10-15,18-26",
        },
        {
            "path": "D:/AgrowAI/knowledge_base/vision/colab/agrowai_v1_training_bundle.zip"
                    "!vision/src/data_pipeline.py",
            "container_sha256": "ac71d389df47cce71e611755037cb8bb52c362c062134ed984f430aa467fabd4",
            "entry_sha256": "9af2fe7d0fe3ce358a22e19b071463000f078d4e960f464196509c1f4ceaa6cb",
        },
        {
            "path": "D:/AgrowAI/knowledge_base/vision/colab/AGROWAI_V1_TRAINING.ipynb",
            "sha256": "dbf0381babf835e0a36913950329914bb5ac8e3e803fceef431e6641b57164da",
            "cells": [8, 26, 28, 30, 36],
        },
        {
            "path": "D:/AgrowAI/model_exports/mobilenetv3_baseline_v1/freeze_inputs/"
                    "runtime_training_config_snapshot.json",
            "sha256": "018769fba169cbe3421d8d6adb9b4fb0af89f1029f2e37460c08cf2cec08ee46",
            "fields": ["model.image_size", "runtime_cfg.image_size", "environment.torchvision_version"],
        },
    ],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ordered_mapping(value: Any) -> list[str]:
    if not isinstance(value, dict):
        raise ValueError("CLASS_MAPPING_OBJECT_REQUIRED")
    mapping = value.get("class_to_index", value)
    if not isinstance(mapping, dict) or not all(isinstance(index, int) for index in mapping.values()):
        raise ValueError("NUMERIC_CLASS_TO_INDEX_REQUIRED")
    ordered = [name for name, _ in sorted(mapping.items(), key=lambda item: item[1])]
    if sorted(mapping.values()) != list(range(len(mapping))):
        raise ValueError("CLASS_INDICES_NOT_CONTIGUOUS")
    return ordered


def verify_inputs() -> dict[str, Any]:
    rows = {}
    for name, path in INPUTS.items():
        if not path.is_file():
            raise FileNotFoundError(f"REQUIRED_INPUT_MISSING:{name}:{path}")
        actual = sha256(path)
        if actual != EXPECTED_HASHES[name]:
            raise RuntimeError(f"INPUT_HASH_MISMATCH:{name}:{actual}")
        rows[name] = {"path": str(path), "sha256": actual, "size_bytes": path.stat().st_size}
    mapping = ordered_mapping(json.loads(INPUTS["class_mapping"].read_text(encoding="utf-8")))
    if mapping != EXPECTED_CLASSES:
        raise RuntimeError("ORDERED_CLASS_MAPPING_MISMATCH")
    rows["ordered_classes"] = mapping
    return rows


def arrays_from_npz(path: Path, expected_shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        logits = next((data[key] for key in ("logits", "_logits", "raw_logits") if key in data), None)
        labels = next((data[key] for key in ("labels", "_labels", "targets", "y_true") if key in data), None)
    if logits is None or labels is None:
        raise RuntimeError(f"LOGITS_OR_LABELS_MISSING:{path}")
    logits = np.asarray(logits, dtype=np.float64)
    labels = np.asarray(labels)
    if logits.shape != expected_shape or labels.shape != (expected_shape[0],):
        raise RuntimeError(f"ARRAY_SHAPE_MISMATCH:{path}:{logits.shape}:{labels.shape}")
    if not np.issubdtype(labels.dtype, np.integer):
        if not np.all(labels == np.round(labels)):
            raise RuntimeError("LABELS_NOT_INTEGER_INDICES")
    labels = labels.astype(np.int64)
    if labels.min() < 0 or labels.max() >= expected_shape[1]:
        raise RuntimeError("LABEL_INDEX_OUT_OF_RANGE")
    if np.all((logits >= 0) & (logits <= 1)) and np.allclose(logits.sum(axis=1), 1, atol=1e-4):
        raise RuntimeError("PROBABILITIES_PROVIDED_INSTEAD_OF_RAW_LOGITS")
    return logits, labels


def nll(logits: np.ndarray, labels: np.ndarray, temperature: float) -> float:
    scaled = logits / temperature
    shifted = scaled - scaled.max(axis=1, keepdims=True)
    logsumexp = np.log(np.exp(shifted).sum(axis=1)) + scaled.max(axis=1)
    return float(np.mean(logsumexp - scaled[np.arange(len(labels)), labels]))


def probabilities(logits: np.ndarray, temperature: float) -> np.ndarray:
    scaled = logits / temperature
    scaled -= scaled.max(axis=1, keepdims=True)
    values = np.exp(scaled)
    return values / values.sum(axis=1, keepdims=True)


def ece(probs: np.ndarray, labels: np.ndarray, bins: int = 15) -> float:
    confidence = probs.max(axis=1)
    correct = probs.argmax(axis=1) == labels
    total = len(labels)
    value = 0.0
    for lower in np.linspace(0, 1, bins + 1)[:-1]:
        upper = lower + 1 / bins
        mask = (confidence > lower) & (confidence <= upper)
        if mask.any():
            value += mask.sum() / total * abs(float(correct[mask].mean()) - float(confidence[mask].mean()))
    return float(value)


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> dict[str, float | bool]:
    import torch
    import torch.nn.functional as functional

    torch.manual_seed(0)
    x = torch.tensor(logits, dtype=torch.float64)
    y = torch.tensor(labels, dtype=torch.long)
    log_temperature = torch.zeros((), dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.LBFGS(
        [log_temperature], lr=0.1, max_iter=200, tolerance_grad=1e-12,
        tolerance_change=1e-14, line_search_fn="strong_wolfe",
    )
    best = {"nll": math.inf, "temperature": 1.0}

    def closure():
        optimizer.zero_grad()
        temperature = log_temperature.exp().clamp(1e-3, 1e3)
        loss = functional.cross_entropy(x / temperature, y)
        loss.backward()
        current = float(loss.detach())
        if current < best["nll"]:
            best.update(nll=current, temperature=float(temperature.detach()))
        return loss

    before = nll(logits, labels, 1.0)
    optimizer.step(closure)
    fitted = float(best["temperature"])
    after = nll(logits, labels, fitted)
    if after > before + 1e-10:
        raise RuntimeError("CALIBRATION_NLL_SAFETY_FAILURE")
    return {
        "temperature": fitted,
        "nll_before": before,
        "nll_after": after,
        "ece_before": ece(probabilities(logits, 1.0), labels),
        "ece_after": ece(probabilities(logits, fitted), labels),
        "improved_nll": after <= before + 1e-10,
    }


def crop_indices() -> dict[str, list[int]]:
    return {
        crop: [EXPECTED_CLASSES.index(class_id) for class_id in classes]
        for crop, classes in CROP_CLASSES.items()
    }


def crop_constrained(
    logits: np.ndarray, labels: np.ndarray, crop: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    indices = np.asarray(crop_indices()[crop])
    mask = np.isin(labels, indices)
    local_labels = np.asarray([list(indices).index(label) for label in labels[mask]], dtype=np.int64)
    return logits[mask][:, indices], local_labels, np.flatnonzero(mask)


@dataclass
class ThresholdRow:
    flow: str
    crop: str
    confidence_threshold: float
    margin_threshold: float
    support: int
    accepted: int
    coverage: float
    accepted_accuracy: float | None
    accepted_errors: int
    zero_accepted_classes: int
    worst_class_coverage: float
    worst_class_accepted_accuracy: float | None
    passes_gate: bool


def threshold_rows(
    probs: np.ndarray, labels: np.ndarray, flow: str, crop: str
) -> list[ThresholdRow]:
    order = np.argsort(probs, axis=1)
    predictions = order[:, -1]
    top1 = probs[np.arange(len(probs)), predictions]
    top2 = probs[np.arange(len(probs)), order[:, -2]]
    rows = []
    for confidence in CONFIDENCE_GRID:
        for margin in MARGIN_GRID:
            accepted_mask = (top1 >= confidence) & ((top1 - top2) >= margin)
            accepted = int(accepted_mask.sum())
            correct = predictions == labels
            class_coverages, class_accuracies, zero = [], [], 0
            for class_index in range(probs.shape[1]):
                class_mask = labels == class_index
                class_support = int(class_mask.sum())
                class_accepted = int((class_mask & accepted_mask).sum())
                coverage = class_accepted / class_support if class_support else 0.0
                class_coverages.append(coverage)
                if not class_accepted:
                    zero += 1
                else:
                    class_accuracies.append(float(correct[class_mask & accepted_mask].mean()))
            accepted_accuracy = float(correct[accepted_mask].mean()) if accepted else None
            worst_accuracy = min(class_accuracies) if class_accuracies else None
            passes = bool(
                accepted
                and zero == 0
                and min(class_coverages) >= 0.50
                and accepted_accuracy is not None and accepted_accuracy >= 0.90
                and worst_accuracy is not None and worst_accuracy >= 0.90
            )
            rows.append(ThresholdRow(
                flow, crop, confidence, margin, len(labels), accepted,
                accepted / len(labels), accepted_accuracy,
                int((accepted_mask & ~correct).sum()), zero,
                min(class_coverages), worst_accuracy, passes,
            ))
    return rows


def select_policy(rows: list[ThresholdRow]) -> ThresholdRow | None:
    eligible = [row for row in rows if row.passes_gate]
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda row: (
            row.coverage,
            row.accepted_accuracy or 0.0,
            -row.confidence_threshold,
            -row.margin_threshold,
        ),
    )


def checkpoint_state_and_metadata(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    import torch

    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict):
        raise RuntimeError("CHECKPOINT_OBJECT_REQUIRED")
    state = next(
        (checkpoint[key] for key in ("model", "model_state_dict", "state_dict") if isinstance(checkpoint.get(key), dict)),
        None,
    )
    if state is None:
        state = checkpoint if checkpoint and all(hasattr(value, "shape") for value in checkpoint.values()) else None
    if state is None:
        raise RuntimeError("MODEL_STATE_NOT_FOUND")
    return state, checkpoint


def checkpoint_mapping(checkpoint: dict[str, Any]) -> list[str] | None:
    for key in ("class_to_index", "class_mapping"):
        value = checkpoint.get(key)
        if isinstance(value, dict):
            try:
                return ordered_mapping(value)
            except ValueError:
                return None
    for key in ("classes", "class_names"):
        value = checkpoint.get(key)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return list(value)
    for value in checkpoint.values():
        if isinstance(value, dict):
            found = checkpoint_mapping(value)
            if found:
                return found
    return None


def verify_checkpoint_identity(state: dict[str, Any], checkpoint: dict[str, Any]) -> dict[str, Any]:
    epoch = checkpoint.get("epoch")
    if epoch != 6:
        raise RuntimeError(f"CHECKPOINT_EPOCH_MISMATCH:{epoch}")
    architecture = (
        checkpoint.get("architecture") or checkpoint.get("arch")
        or checkpoint.get("model_name") or checkpoint.get("model")
    )
    if isinstance(architecture, str):
        normalized = architecture.lower().replace("-", "_").replace(" ", "_")
        if "mobilenetv3" not in normalized and "mobilenet_v3" not in normalized:
            raise RuntimeError(f"CHECKPOINT_ARCHITECTURE_MISMATCH:{architecture}")
    mapping = checkpoint_mapping(checkpoint)
    if mapping != EXPECTED_CLASSES:
        raise RuntimeError("CHECKPOINT_ORDERED_MAPPING_MISMATCH")
    dimensions = {
        str(key): list(value.shape)
        for key, value in state.items() if hasattr(value, "shape")
    }
    output_tensors = [
        {"key": key, "shape": shape}
        for key, shape in dimensions.items()
        if len(shape) in (1, 2) and 9 in shape
    ]
    if not output_tensors:
        raise RuntimeError("CHECKPOINT_NINE_CLASS_OUTPUT_NOT_FOUND")
    return {
        "epoch": epoch, "architecture": architecture,
        "ordered_mapping": mapping, "nine_class_output_tensors": output_tensors,
    }


def normalize_state_keys(state: dict[str, Any]) -> dict[str, Any]:
    normalized = {}
    for key, value in state.items():
        clean = str(key)
        for prefix in ("module.", "model."):
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
        normalized[clean] = value
    return normalized


def extract_preprocessing_definition(evidence: dict[Any, Any]) -> dict[str, Any]:
    """Validate a frozen, source-backed inference preprocessing definition."""
    if not isinstance(evidence, dict):
        raise RuntimeError("PREPROCESSING_EVIDENCE_OBJECT_REQUIRED")
    decision = evidence.get("decision")
    if decision not in PREPROCESSING_DECISIONS:
        raise RuntimeError("INVALID_PREPROCESSING_DECISION")
    if decision != "PREPROCESSING_PROVEN":
        raise RuntimeError("EXACT_PREPROCESSING_NOT_PROVEN")

    inference = evidence.get("inference")
    if not isinstance(inference, dict):
        raise RuntimeError("INFERENCE_PREPROCESSING_MISSING")
    resize = inference.get("resize")
    normalization = inference.get("normalization")
    required = {
        "image_size": inference.get("image_size"),
        "resize": resize,
        "tensor_conversion": inference.get("tensor_conversion"),
        "normalization": normalization,
    }
    if any(value is None for value in required.values()):
        raise RuntimeError("INCOMPLETE_INFERENCE_PREPROCESSING")
    if not isinstance(resize, dict) or resize.get("size") != [224, 224]:
        raise RuntimeError("INFERENCE_RESIZE_NOT_PROVEN")
    if resize.get("crop") is not None:
        raise RuntimeError("UNEXPECTED_INFERENCE_CROP")
    if not isinstance(normalization, dict):
        raise RuntimeError("INFERENCE_NORMALIZATION_NOT_PROVEN")
    mean = normalization.get("mean")
    std = normalization.get("std")
    if mean != [0.485, 0.456, 0.406] or std != [0.229, 0.224, 0.225]:
        raise RuntimeError("INFERENCE_NORMALIZATION_CONFLICT")
    if not evidence.get("evidence"):
        raise RuntimeError("PREPROCESSING_SOURCE_EVIDENCE_MISSING")

    # Copy through JSON so integer dictionary keys in loaded checkpoint metadata
    # cannot break path traversal or leak mutable input into the frozen config.
    normalized = json.loads(json.dumps(evidence))
    normalized["image_size"] = inference["image_size"]
    normalized["mean"] = mean
    normalized["std"] = std
    return normalized


def preprocessing(snapshot: dict[Any, Any], checkpoint: dict[Any, Any]) -> dict[str, Any]:
    """Gate reconstruction on the recovered source definition and corroborating size."""
    observed_sizes: set[int] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key).lower() in {"image_size", "img_size", "input_size"}:
                    if isinstance(item, int):
                        observed_sizes.add(item)
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk({"snapshot": snapshot, "checkpoint": checkpoint})
    frozen = extract_preprocessing_definition(FROZEN_PREPROCESSING_EVIDENCE)
    if observed_sizes and observed_sizes != {int(frozen["image_size"])}:
        raise RuntimeError(f"PREPROCESSING_AMBIGUOUS:{sorted(observed_sizes)}")
    if not observed_sizes:
        raise RuntimeError("PREPROCESSING_IMAGE_SIZE_NOT_CORROBORATED")
    return frozen


def build_model(state: dict[str, Any]):
    from torchvision.models import mobilenet_v3_small

    model = mobilenet_v3_small(weights=None)
    model.classifier[3] = __import__("torch").nn.Linear(model.classifier[3].in_features, 9)
    model.load_state_dict(normalize_state_keys(state), strict=True)
    model.eval()
    return model


def export_and_parity(model: Any, image_size: int, onnx_path: Path) -> dict[str, Any]:
    import onnx
    import onnxruntime
    import torch

    torch.manual_seed(20260727)
    samples = torch.randn(4, 3, int(image_size), int(image_size), dtype=torch.float32)
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model, samples[:1], onnx_path, input_names=["image"], output_names=["logits"],
        dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17, do_constant_folding=True,
    )
    graph = onnx.load(str(onnx_path))
    onnx.checker.check_model(graph)
    session = onnxruntime.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    with torch.inference_mode():
        torch_output = model(samples).cpu().numpy()
    onnx_output = session.run(None, {session.get_inputs()[0].name: samples.numpy()})[0]
    difference = np.abs(torch_output - onnx_output)
    passed = torch_output.shape == (4, 9) and onnx_output.shape == (4, 9) and np.allclose(
        torch_output, onnx_output, rtol=1e-4, atol=1e-5
    )
    return {
        "opset": 17, "input_name": session.get_inputs()[0].name,
        "output_name": session.get_outputs()[0].name,
        "pytorch_shape": list(torch_output.shape), "onnx_shape": list(onnx_output.shape),
        "max_abs_difference": float(difference.max()),
        "mean_abs_difference": float(difference.mean()),
        "rtol": 1e-4, "atol": 1e-5, "passed": bool(passed),
        "synthetic_inputs_only": True, "provisional_test_images_opened": False,
    }


def square_image_size(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, (list, tuple)) and value:
        dimensions = [int(item) for item in value[-2:]]
        if len(set(dimensions)) == 1:
            return dimensions[0]
    raise RuntimeError("SQUARE_IMAGE_SIZE_REQUIRED")


def manifest_for(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and "bundle/artifact_manifest.json" not in str(path).replace("\\", "/") and path.name != "SHA256SUMS.txt":
            rows.append({"path": path.relative_to(root).as_posix(), "sha256": sha256(path), "size_bytes": path.stat().st_size})
    return rows


def reconstruct(output: Path) -> dict[str, Any]:
    verified = verify_inputs()
    state, checkpoint = checkpoint_state_and_metadata(INPUTS["checkpoint"])
    checkpoint_identity = verify_checkpoint_identity(state, checkpoint)
    snapshot = json.loads(INPUTS["runtime_snapshot"].read_text(encoding="utf-8"))
    preproc = preprocessing(snapshot, checkpoint)

    # Calibration, threshold reconstruction, model loading and export remain
    # unreachable until the exact preprocessing gate above succeeds.
    dev_logits, dev_labels = arrays_from_npz(INPUTS["dev_logits"], (1320, 9))
    calibration_logits, calibration_labels = arrays_from_npz(INPUTS["calibration_logits"], (660, 9))
    del dev_logits, dev_labels  # verified development evidence; never used to tune calibration.
    global_calibration = fit_temperature(calibration_logits, calibration_labels)
    global_calibration["historical_receipt_temperature"] = HISTORICAL_TEMPERATURE
    global_calibration["absolute_difference_from_historical"] = abs(
        float(global_calibration["temperature"]) - HISTORICAL_TEMPERATURE
    )

    all_rows = threshold_rows(
        probabilities(calibration_logits, float(global_calibration["temperature"])),
        calibration_labels, "global_joint", "all",
    )
    selected: dict[str, Any] = {}
    crop_calibrations: dict[str, Any] = {}
    crop_requires_separate_calibration = False
    for crop in CROP_CLASSES:
        local_logits, local_labels, _ = crop_constrained(calibration_logits, calibration_labels, crop)
        local_fit = fit_temperature(local_logits, local_labels)
        crop_calibrations[crop] = local_fit
        if local_fit["nll_after"] < nll(local_logits, local_labels, float(global_calibration["temperature"])) - 1e-6:
            crop_requires_separate_calibration = True
        crop_rows = threshold_rows(
            probabilities(local_logits, float(local_fit["temperature"])),
            local_labels, "crop_constrained", crop,
        )
        all_rows.extend(crop_rows)
        policy = select_policy(crop_rows)
        selected[crop] = vars(policy) if policy else None

    model = build_model(state)

    output.mkdir(parents=True, exist_ok=True)
    checkpoint_out = output / "checkpoint/best.pt"
    checkpoint_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(INPUTS["checkpoint"], checkpoint_out)
    write_json(output / "runtime/class_mapping.json", {
        "class_to_index": {name: index for index, name in enumerate(EXPECTED_CLASSES)},
        "ordered_classes": EXPECTED_CLASSES,
    })
    runtime_config = {
        "model_name": "mobilenetv3_small", "model_version": "legacy_joint_v1_reconstructed",
        "output_classes": 9, "preprocessing": preproc,
        "routing": {
            crop: {"allowed_class_ids": classes, "user_crop_confirmation_required": True}
            for crop, classes in CROP_CLASSES.items()
        },
        "logit_masking_policy": (
            "Crop-constrained softmax, calibration and abstention must be applied together; "
            "global probabilities must never be silently masked after calibration."
        ),
    }
    write_json(output / "runtime/runtime_config.json", runtime_config)
    write_json(output / "calibration/temperature.json", {
        "global": global_calibration["temperature"],
        "per_crop": {crop: values["temperature"] for crop, values in crop_calibrations.items()},
        "source_split": "calibration", "provisional_outputs_used": False,
    })
    write_json(output / "calibration/temperature_metrics.json", {
        "global": global_calibration, "per_crop": crop_calibrations,
        "crop_constrained_calibration_required": crop_requires_separate_calibration,
    })
    threshold_path = output / "thresholds/threshold_search_results.csv"
    threshold_path.parent.mkdir(parents=True, exist_ok=True)
    with threshold_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(vars(all_rows[0])))
        writer.writeheader()
        writer.writerows(vars(row) for row in all_rows)
    write_json(output / "thresholds/abstention_policy.json", {
        "objective": (
            "Maximize calibration coverage subject to: every supported class has accepted "
            "samples, worst-class coverage >= 0.50, overall and worst-class accepted accuracy >= 0.90."
        ),
        "confidence_grid": CONFIDENCE_GRID, "margin_grid": MARGIN_GRID,
        "tie_break": "higher coverage, then accepted accuracy, then lower confidence and margin",
        "selected_crop_constrained_policies": selected,
        "source_split": "calibration", "historical_threshold_copied": False,
        "provisional_outputs_used": False,
    })
    onnx_path = output / "onnx/model_opset17.onnx"
    parity = export_and_parity(model, square_image_size(preproc["image_size"]), onnx_path)
    write_json(output / "onnx/export_receipt.json", {
        "checkpoint_sha256": EXPECTED_HASHES["checkpoint"], "onnx_sha256": sha256(onnx_path),
        "opset": 17, "output_classes": 9, "export_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    })
    write_json(output / "onnx/parity_receipt.json", parity)
    write_json(output / "lineage/model_lineage.json", {
        "inputs": verified, "checkpoint_epoch": checkpoint.get("epoch"),
        "architecture": checkpoint.get("architecture") or checkpoint.get("arch") or checkpoint.get("model_name"),
        "checkpoint_identity": checkpoint_identity,
        "development_used_for_tuning": False, "calibration_used_for_calibration_and_thresholds": True,
        "provisional_test_used": False,
    })

    policies_ready = all(selected.values())
    if not parity["passed"]:
        final = "RECONSTRUCTION_FAILED"
    elif not policies_ready:
        final = "REQUIRES_THRESHOLD_REVIEW"
    elif crop_requires_separate_calibration:
        # Per-crop values are reconstructed, but require review before integration.
        final = "REQUIRES_CROP_CONSTRAINED_RECALIBRATION"
    else:
        final = "READY_FOR_BACKEND_INTEGRATION"
    assert final in VALID_DECISIONS
    decision = {
        "decision": final, "checkpoint_verified": True, "onnx_opset": 17,
        "parity_passed": parity["passed"], "all_crop_threshold_policies_selected": bool(policies_ready),
        "separate_crop_constrained_calibration_required": crop_requires_separate_calibration,
        "app_exposure_allowed": False, "provisional_test_opened": False,
    }
    write_json(output / "reports/runtime_reconstruction_decision.json", decision)
    report = [
        "# Legacy Joint V1 Runtime Reconstruction",
        "", f"Decision: **{final}**", "",
        f"Reconstructed temperature: {global_calibration['temperature']}",
        f"Historical receipt temperature: {HISTORICAL_TEMPERATURE}",
        f"Absolute difference: {global_calibration['absolute_difference_from_historical']}",
        f"Separate crop-constrained calibration required: {crop_requires_separate_calibration}",
        "", "Thresholds were selected exclusively from calibration evidence. Provisional-test outputs were not opened or used.",
        "", "The app remains disabled pending backend integration review.",
    ]
    report_path = output / "reports/runtime_reconstruction_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    artifacts = manifest_for(output)
    write_json(output / "bundle/artifact_manifest.json", {
        "bundle_version": "legacy_joint_v1_reconstructed", "artifacts": artifacts,
    })
    sums_path = output / "bundle/SHA256SUMS.txt"
    sums_path.parent.mkdir(parents=True, exist_ok=True)
    sums_path.write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in artifacts), encoding="utf-8"
    )
    verified_bundle = all(sha256(output / row["path"]) == row["sha256"] for row in artifacts)
    write_json(output / "bundle/bundle_verification.json", {
        "verified": verified_bundle, "artifact_count": len(artifacts),
        "verification_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    })
    if not verified_bundle:
        raise RuntimeError("BUNDLE_VERIFICATION_FAILED")
    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="/content/drive/MyDrive/AgrowAI_V1/deployment_exports/legacy_joint_v1_reconstructed",
    )
    args = parser.parse_args()
    try:
        decision = reconstruct(Path(args.output_dir))
        print(f"FINAL_DECISION={decision['decision']}")
    except Exception as exc:
        print(f"FINAL_DECISION=RECONSTRUCTION_FAILED category={type(exc).__name__}")
        raise
    finally:
        print("AGROWAI_LEGACY_JOINT_RUNTIME_RECONSTRUCTION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
