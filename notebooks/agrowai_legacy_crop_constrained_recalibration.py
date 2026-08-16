"""Reconstruct crop-constrained calibration and runtime artifacts from frozen evidence."""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:
    from notebooks.agrowai_legacy_joint_runtime_reconstruction import (
        CROP_CLASSES,
        EXPECTED_CLASSES,
        EXPECTED_HASHES,
        FROZEN_PREPROCESSING_EVIDENCE,
        INPUTS,
        arrays_from_npz,
        build_model,
        checkpoint_state_and_metadata,
        crop_constrained,
        crop_indices,
        ece,
        fit_temperature,
        manifest_for,
        nll,
        preprocessing,
        probabilities,
        select_policy,
        sha256,
        threshold_rows,
        verify_checkpoint_identity,
        verify_inputs,
        write_json,
    )
except ModuleNotFoundError:  # Colab: both scripts may be copied into one directory.
    from agrowai_legacy_joint_runtime_reconstruction import (
    CROP_CLASSES,
    EXPECTED_CLASSES,
    EXPECTED_HASHES,
    FROZEN_PREPROCESSING_EVIDENCE,
    INPUTS,
    arrays_from_npz,
    build_model,
    checkpoint_state_and_metadata,
    crop_constrained,
    crop_indices,
    ece,
    fit_temperature,
    manifest_for,
    nll,
    preprocessing,
    probabilities,
    select_policy,
    sha256,
    threshold_rows,
    verify_checkpoint_identity,
    verify_inputs,
    write_json,
    )

DEFAULT_OUTPUT = Path(
    "/content/drive/MyDrive/AgrowAI_V1/deployment_exports/"
    "legacy_joint_v1_crop_constrained"
)
CURRENT_ONNX = Path(
    "/content/drive/MyDrive/AgrowAI_V1/exports/"
    "mobilenetv3_small_v1/agrowai_v1_classifier.onnx"
)
MIN_CALIBRATION_PER_CLASS = 2
FINAL_DECISIONS = {
    "READY_FOR_BACKEND_INTEGRATION",
    "REQUIRES_THRESHOLD_REVIEW",
    "INSUFFICIENT_CROP_CALIBRATION_DATA",
    "ONNX_EXPORT_FAILED",
    "PARITY_FAILED",
    "REQUIRES_RETRAINING",
    "RECALIBRATION_FAILED",
}


def constrain_logits_for_crop(logits: np.ndarray, crop: str) -> np.ndarray:
    """Restrict raw logits before calibration or softmax."""
    if crop not in CROP_CLASSES:
        raise ValueError(f"UNKNOWN_CROP:{crop}")
    return np.asarray(logits)[:, np.asarray(crop_indices()[crop])]


def verify_routing_policy() -> dict[str, Any]:
    groups = crop_indices()
    flattened = [index for values in groups.values() for index in values]
    if sorted(flattened) != list(range(len(EXPECTED_CLASSES))):
        raise RuntimeError("CROP_ROUTING_PARTITION_INVALID")
    if len(flattened) != len(set(flattened)):
        raise RuntimeError("CROP_ROUTING_CLASS_LEAK")
    return {
        "routing_input": "explicit_user_crop_confirmation",
        "ai_crop_verification": False,
        "user_crop_confirmation_required": True,
        "restrict_logits_before_calibration_and_softmax": True,
        "groups": {
            crop: {
                "global_indices": groups[crop],
                "class_ids": classes,
                "forbidden_class_ids": [
                    item for item in EXPECTED_CLASSES if item not in classes
                ],
            }
            for crop, classes in CROP_CLASSES.items()
        },
    }


def class_metrics(
    predictions: np.ndarray, labels: np.ndarray, class_names: list[str]
) -> tuple[float, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    f1_values = []
    for index, name in enumerate(class_names):
        true_positive = int(((predictions == index) & (labels == index)).sum())
        false_positive = int(((predictions == index) & (labels != index)).sum())
        false_negative = int(((predictions != index) & (labels == index)).sum())
        support = int((labels == index).sum())
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = true_positive / support if support else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        f1_values.append(f1)
        rows.append(
            {
                "class_index": index,
                "class_name": name,
                "support": support,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    return float(np.mean(f1_values)), rows


def evaluate_development(
    logits: np.ndarray,
    labels: np.ndarray,
    temperature: float,
    confidence_threshold: float,
    margin_threshold: float,
    class_names: list[str],
) -> dict[str, Any]:
    probs = probabilities(logits, temperature)
    order = np.argsort(probs, axis=1)
    predictions = order[:, -1]
    top1 = probs[np.arange(len(probs)), predictions]
    top2 = probs[np.arange(len(probs)), order[:, -2]]
    accepted = (top1 >= confidence_threshold) & (
        (top1 - top2) >= margin_threshold
    )
    correct = predictions == labels
    macro_f1, per_class = class_metrics(predictions, labels, class_names)
    return {
        "label": "DEVELOPMENT_ONLY_NOT_AN_OFFICIAL_ACCURACY_CLAIM",
        "sample_count": len(labels),
        "coverage": float(accepted.mean()),
        "accepted_count": int(accepted.sum()),
        "abstention_count": int((~accepted).sum()),
        "accepted_accuracy": (
            float(correct[accepted].mean()) if accepted.any() else None
        ),
        "accepted_errors": int((accepted & ~correct).sum()),
        "false_confident_errors": int((accepted & ~correct).sum()),
        "macro_f1_all_predictions": macro_f1,
        "per_class": per_class,
        "nll": nll(logits, labels, temperature),
        "ece": ece(probs, labels),
    }


def actual_onnx_opset(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "path": str(path), "actual_opset": None}
    import onnx

    graph = onnx.load(str(path), load_external_data=False)
    versions = {item.domain or "ai.onnx": int(item.version) for item in graph.opset_import}
    return {
        "exists": True,
        "path": str(path),
        "sha256": sha256(path),
        "opset_imports": versions,
        "actual_opset": versions.get("ai.onnx"),
    }


def export_opset17_and_parity(model: Any, output_path: Path) -> dict[str, Any]:
    import onnx
    import onnxruntime
    import torch

    torch.manual_seed(1729)
    samples = torch.randn(4, 3, 224, 224, dtype=torch.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        samples[:1],
        output_path,
        input_names=["image"],
        output_names=["logits"],
        dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )
    graph = onnx.load(str(output_path))
    onnx.checker.check_model(graph)
    versions = {item.domain or "ai.onnx": int(item.version) for item in graph.opset_import}
    actual_opset = versions.get("ai.onnx")
    if actual_opset != 17:
        raise RuntimeError(f"ONNX_ACTUAL_OPSET_NOT_17:{actual_opset}")

    session = onnxruntime.InferenceSession(
        str(output_path), providers=["CPUExecutionProvider"]
    )
    input_meta = session.get_inputs()[0]
    output_meta = session.get_outputs()[0]
    if input_meta.shape[1:] != [3, 224, 224]:
        raise RuntimeError(f"ONNX_INPUT_SHAPE_INVALID:{input_meta.shape}")
    if output_meta.shape[-1] != 9:
        raise RuntimeError(f"ONNX_OUTPUT_SHAPE_INVALID:{output_meta.shape}")
    with torch.inference_mode():
        torch_values = model(samples).cpu().numpy()
    onnx_values = session.run(None, {input_meta.name: samples.numpy()})[0]
    difference = np.abs(torch_values - onnx_values)
    passed = bool(
        torch_values.shape == onnx_values.shape == (4, 9)
        and np.allclose(torch_values, onnx_values, rtol=1e-4, atol=1e-5)
    )
    return {
        "actual_opset": actual_opset,
        "input_name": input_meta.name,
        "input_shape": input_meta.shape,
        "output_name": output_meta.name,
        "output_shape": output_meta.shape,
        "max_abs_difference": float(difference.max()),
        "mean_abs_difference": float(difference.mean()),
        "rtol": 1e-4,
        "atol": 1e-5,
        "passed": passed,
        "synthetic_inputs_only": True,
        "parity_before_crop_restriction": True,
    }


def validate_crop_support(labels: np.ndarray, crop: str) -> dict[str, Any]:
    _, local_labels, _ = crop_constrained(np.zeros((len(labels), 9)), labels, crop)
    counts = {
        class_name: int((local_labels == index).sum())
        for index, class_name in enumerate(CROP_CLASSES[crop])
    }
    if not len(local_labels) or any(value < MIN_CALIBRATION_PER_CLASS for value in counts.values()):
        raise RuntimeError(f"INSUFFICIENT_CROP_CALIBRATION_DATA:{crop}:{counts}")
    return {"sample_count": len(local_labels), "per_class_counts": counts}


def run(output: Path) -> dict[str, Any]:
    verified = verify_inputs()
    state, checkpoint = checkpoint_state_and_metadata(INPUTS["checkpoint"])
    checkpoint_identity = verify_checkpoint_identity(state, checkpoint)
    snapshot = json.loads(INPUTS["runtime_snapshot"].read_text(encoding="utf-8"))
    frozen_preprocessing = preprocessing(snapshot, checkpoint)
    routing = verify_routing_policy()

    calibration_logits, calibration_labels = arrays_from_npz(
        INPUTS["calibration_logits"], (660, 9)
    )
    development_logits, development_labels = arrays_from_npz(
        INPUTS["dev_logits"], (1320, 9)
    )

    calibration_metrics: dict[str, Any] = {}
    development_metrics: dict[str, Any] = {}
    policies: dict[str, Any] = {}
    search_rows = []
    for crop in ("paddy", "cotton", "groundnut"):
        support = validate_crop_support(calibration_labels, crop)
        crop_cal_logits, crop_cal_labels, _ = crop_constrained(
            calibration_logits, calibration_labels, crop
        )
        fitted = fit_temperature(crop_cal_logits, crop_cal_labels)
        if fitted["nll_after"] > fitted["nll_before"] + 1e-10:
            raise RuntimeError(f"RECALIBRATION_FAILED:{crop}:NLL_WORSENED")
        fitted.update(support)
        fitted.update(
            {
                "crop": crop,
                "source_split": "calibration",
                "optimizer": "torch.optim.LBFGS on log_temperature",
                "seed": 0,
                "checkpoint_sha256": EXPECTED_HASHES["checkpoint"],
                "calibration_logits_sha256": EXPECTED_HASHES["calibration_logits"],
                "provisional_test_used": False,
            },
        )
        calibration_metrics[crop] = fitted

        rows = threshold_rows(
            probabilities(crop_cal_logits, float(fitted["temperature"])),
            crop_cal_labels,
            "crop_constrained",
            crop,
        )
        search_rows.extend(rows)
        selected = select_policy(rows)
        if selected is None:
            policies[crop] = None
            continue
        policy = asdict(selected)
        policy.update(
            {
                "source_split": "calibration",
                "temperature": fitted["temperature"],
                "user_crop_confirmation_required": True,
                "provisional_test_used": False,
            }
        )
        policies[crop] = policy

        crop_dev_logits, crop_dev_labels, _ = crop_constrained(
            development_logits, development_labels, crop
        )
        development_metrics[crop] = evaluate_development(
            crop_dev_logits,
            crop_dev_labels,
            float(fitted["temperature"]),
            float(selected.confidence_threshold),
            float(selected.margin_threshold),
            CROP_CLASSES[crop],
        )

    if any(value is None for value in policies.values()):
        final_decision = "REQUIRES_THRESHOLD_REVIEW"
    else:
        final_decision = "READY_FOR_BACKEND_INTEGRATION"

    output.mkdir(parents=True, exist_ok=True)
    write_json(
        output / "runtime/class_mapping.json",
        {
            "ordered_classes": EXPECTED_CLASSES,
            "class_to_index": {
                name: index for index, name in enumerate(EXPECTED_CLASSES)
            },
        },
    )
    write_json(output / "runtime/preprocessing.json", frozen_preprocessing)
    write_json(output / "runtime/crop_routing_policy.json", routing)
    for crop in ("paddy", "cotton", "groundnut"):
        write_json(
            output / f"calibration/{crop}_temperature.json",
            calibration_metrics[crop],
        )
        write_json(
            output / f"thresholds/{crop}_abstention_policy.json",
            policies[crop]
            or {
                "crop": crop,
                "status": "NO_SAFE_POLICY_SELECTED",
                "source_split": "calibration",
            },
        )
    write_json(
        output / "calibration/crop_calibration_metrics.json", calibration_metrics
    )
    threshold_path = output / "thresholds/crop_threshold_search_results.csv"
    threshold_path.parent.mkdir(parents=True, exist_ok=True)
    with threshold_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(search_rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in search_rows)

    previous_onnx = actual_onnx_opset(CURRENT_ONNX)
    model = build_model(state)
    onnx_path = output / "onnx/model_opset17.onnx"
    parity = export_opset17_and_parity(model, onnx_path)
    if not parity["passed"]:
        final_decision = "PARITY_FAILED"
    write_json(
        output / "onnx/export_receipt.json",
        {
            "checkpoint_sha256": EXPECTED_HASHES["checkpoint"],
            "onnx_sha256": sha256(onnx_path),
            "requested_opset": 17,
            "actual_opset": parity["actual_opset"],
            "exporter": "torch.onnx.export",
            "dynamo": False,
            "previous_export_inspection": previous_onnx,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
    )
    write_json(output / "onnx/parity_receipt.json", parity)
    write_json(
        output / "lineage/model_lineage.json",
        {
            "verified_inputs": verified,
            "checkpoint_identity": checkpoint_identity,
            "preprocessing_decision": FROZEN_PREPROCESSING_EVIDENCE["decision"],
            "development_used_for_reporting_only": True,
            "calibration_used_for_temperature_and_threshold_selection": True,
            "provisional_test_used": False,
            "model_weights_modified": False,
        },
    )

    if final_decision not in FINAL_DECISIONS:
        raise RuntimeError(f"INVALID_FINAL_DECISION:{final_decision}")
    decision = {
        "decision": final_decision,
        "crop_policies_ready": {
            crop: policies[crop] is not None for crop in policies
        },
        "actual_onnx_opset": parity["actual_opset"],
        "parity_passed": parity["passed"],
        "app_enablement_allowed": False,
        "backend_integration_performed": False,
        "provisional_test_opened": False,
    }
    write_json(output / "reports/crop_constrained_recalibration_decision.json", decision)
    report_lines = [
        "# Legacy Joint Crop-Constrained Recalibration",
        "",
        f"Final decision: **{final_decision}**",
        "",
        "All temperatures and thresholds were selected from calibration evidence only.",
        "Development subsets were used only for development-labelled reporting.",
        "Provisional-test material was not opened or used.",
        "",
        "## Crop results",
        "",
    ]
    for crop in ("paddy", "cotton", "groundnut"):
        report_lines.extend(
            [
                f"### {crop.title()}",
                "",
                f"- Calibration: `{json.dumps(calibration_metrics[crop], sort_keys=True)}`",
                f"- Policy: `{json.dumps(policies[crop], sort_keys=True)}`",
                f"- Development-only: `{json.dumps(development_metrics.get(crop), sort_keys=True)}`",
                "",
            ]
        )
    report_lines.extend(
        [
            "## ONNX",
            "",
            f"- Previous export inspection: `{json.dumps(previous_onnx, sort_keys=True)}`",
            f"- New export actual opset: `{parity['actual_opset']}`",
            f"- Synthetic parity passed: `{parity['passed']}`",
        ]
    )
    report_path = output / "reports/crop_constrained_recalibration_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    artifacts = manifest_for(output)
    write_json(
        output / "bundle/artifact_manifest.json",
        {
            "bundle_version": "legacy_joint_v1_crop_constrained",
            "artifacts": artifacts,
        },
    )
    sums = output / "bundle/SHA256SUMS.txt"
    sums.parent.mkdir(parents=True, exist_ok=True)
    sums.write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in artifacts),
        encoding="utf-8",
    )
    verified_bundle = all(
        sha256(output / row["path"]) == row["sha256"] for row in artifacts
    )
    write_json(
        output / "bundle/bundle_verification.json",
        {
            "verified": verified_bundle,
            "artifact_count": len(artifacts),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
    )
    if not verified_bundle:
        raise RuntimeError("BUNDLE_VERIFICATION_FAILED")
    return decision


def classify_failure(exc: Exception) -> str:
    message = str(exc)
    if "INSUFFICIENT_CROP_CALIBRATION_DATA" in message:
        return "INSUFFICIENT_CROP_CALIBRATION_DATA"
    if "ONNX" in message:
        return "ONNX_EXPORT_FAILED"
    if "PARITY" in message:
        return "PARITY_FAILED"
    if "CALIBRATION" in message or "RECALIBRATION" in message:
        return "RECALIBRATION_FAILED"
    return "REQUIRES_RETRAINING"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    try:
        decision = run(Path(args.output_dir))
        print(f"FINAL_DECISION={decision['decision']}")
        return 0
    except Exception as exc:
        print(f"FINAL_DECISION={classify_failure(exc)}")
        raise
    finally:
        print("AGROWAI_LEGACY_CROP_CONSTRAINED_RECALIBRATION_COMPLETE")


if __name__ == "__main__":
    raise SystemExit(main())
