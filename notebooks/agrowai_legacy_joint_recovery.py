"""Read-only lineage recovery for the AgrowAI legacy nine-class joint model.

This program inventories and cross-checks existing evidence. It never trains,
recalibrates, reconstructs thresholds, opens provisional-test images, or
modifies source artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

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
VALID_DECISIONS = {
    "READY_FOR_RUNTIME_RECONSTRUCTION",
    "READY_FOR_RECALIBRATION_FROM_EXISTING_CALIBRATION_SPLIT",
    "READY_FOR_THRESHOLD_RECONSTRUCTION_FROM_EXISTING_CALIBRATION_SPLIT",
    "REQUIRES_ONNX_REEXPORT",
    "REQUIRES_RETRAINING",
    "LINEAGE_AMBIGUOUS",
}
MODEL_SUFFIXES = {".pt", ".pth"}
PROVISIONAL_ALLOWED_NAMES = {
    "provisional_test_metrics.json",
    "one_time_evaluation_receipt.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def flatten_strings(value: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten_strings(item, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from flatten_strings(item, f"{prefix}[{index}]")
    elif isinstance(value, (str, int, float, bool)):
        yield prefix, str(value)


def artifact_paths(audit: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for item in audit.get("artifacts", []):
        raw = item.get("path") or item.get("absolute_or_repository_path")
        if raw:
            path = Path(raw)
            if path.is_file():
                paths.append(path)
    return sorted(set(paths), key=lambda value: str(value).lower())


def find_named(paths: list[Path], name: str) -> list[Path]:
    return [path for path in paths if path.name.lower() == name.lower()]


def class_mapping_from(value: Any) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    if isinstance(value, dict):
        for key in ("class_to_index", "class_mapping", "classes", "class_names", "idx_to_class"):
            if key not in value:
                continue
            candidate = value[key]
            if isinstance(candidate, list) and all(isinstance(item, str) for item in candidate):
                return candidate
            if isinstance(candidate, dict):
                if all(isinstance(v, int) for v in candidate.values()):
                    return [k for k, _ in sorted(candidate.items(), key=lambda item: item[1])]
                if all(str(k).isdigit() for k in candidate):
                    return [str(v) for k, v in sorted(candidate.items(), key=lambda item: int(item[0]))]
        for nested in value.values():
            result = class_mapping_from(nested)
            if result:
                return result
    return None


def state_dict_from(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    for key in ("model", "model_state_dict", "state_dict"):
        candidate = value.get(key)
        if isinstance(candidate, dict):
            return candidate
    if value and all(hasattr(item, "shape") for item in value.values()):
        return value
    return None


def checkpoint_metadata(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "loaded_on": "cpu",
        "safe_weights_only": True,
    }
    try:
        import torch

        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as exc:
        result.update({
            "inspection_status": "SAFE_LOAD_FAILED",
            "error_category": type(exc).__name__,
        })
        return result
    result["inspection_status"] = "INSPECTED"
    if isinstance(checkpoint, dict):
        result["checkpoint_keys"] = sorted(str(key) for key in checkpoint)
        for key in ("epoch", "architecture", "arch", "model_name", "model_version",
                    "best_metric", "best_loss", "metrics", "config", "cfg",
                    "training_config", "manifest_sha256", "split_manifest_sha256"):
            if key in checkpoint:
                item = checkpoint[key]
                result[key] = item if isinstance(item, (str, int, float, bool, list, dict, type(None))) else str(type(item))
        mapping = class_mapping_from(checkpoint)
        if mapping:
            result["class_mapping"] = mapping
    state = state_dict_from(checkpoint)
    if state is not None:
        dimensions = {}
        for key, tensor in state.items():
            shape = getattr(tensor, "shape", None)
            if shape is not None:
                dimensions[str(key)] = [int(part) for part in shape]
        result["state_tensor_dimensions"] = dimensions
        likely_outputs = [
            {"key": key, "shape": shape}
            for key, shape in dimensions.items()
            if len(shape) in (1, 2) and 9 in shape
        ]
        result["possible_nine_class_output_tensors"] = likely_outputs
        result["model_output_dimension_supported"] = bool(likely_outputs)
    return result


def json_evidence(paths: list[Path], name: str) -> list[dict[str, Any]]:
    rows = []
    for path in find_named(paths, name):
        try:
            content = load_json(path)
            rows.append({"path": str(path), "sha256": sha256(path), "content": content})
        except Exception as exc:
            rows.append({"path": str(path), "error_category": type(exc).__name__})
    return rows


def lineage_documents(paths: list[Path]) -> list[dict[str, Any]]:
    """Load metadata JSON, excluding all provisional material except approved reports."""
    rows = []
    for path in paths:
        if path.suffix.lower() != ".json":
            continue
        lowered = str(path).lower()
        if "provisional" in lowered and path.name.lower() not in PROVISIONAL_ALLOWED_NAMES:
            continue
        try:
            rows.append({"path": str(path), "sha256": sha256(path), "content": load_json(path)})
        except Exception:
            continue
    return rows


def referenced_hashes(value: Any) -> set[str]:
    hashes = set()
    for _, text in flatten_strings(value):
        lowered = text.lower()
        if len(lowered) == 64 and all(char in "0123456789abcdef" for char in lowered):
            hashes.add(lowered)
    return hashes


def inspect_npz_metadata(path: Path) -> dict[str, Any]:
    """Inspect arrays only; never scores, predictions, or image paths."""
    try:
        import numpy as np

        with np.load(path, allow_pickle=False) as data:
            return {
                "path": str(path),
                "sha256": sha256(path),
                "keys": sorted(data.files),
                "arrays": {
                    key: {"shape": list(data[key].shape), "dtype": str(data[key].dtype)}
                    for key in data.files
                },
            }
    except Exception as exc:
        return {"path": str(path), "error_category": type(exc).__name__}


def inspect_onnx(path: Path) -> dict[str, Any]:
    result = {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}
    try:
        import onnx

        model = onnx.load(str(path), load_external_data=False)
        result["inspection_status"] = "INSPECTED"
        result["opsets"] = [
            {"domain": item.domain or "ai.onnx", "version": int(item.version)}
            for item in model.opset_import
        ]
        result["inputs"] = [
            {
                "name": item.name,
                "shape": [
                    dim.dim_value if dim.HasField("dim_value") else dim.dim_param or None
                    for dim in item.type.tensor_type.shape.dim
                ],
            }
            for item in model.graph.input
        ]
        result["outputs"] = [
            {
                "name": item.name,
                "shape": [
                    dim.dim_value if dim.HasField("dim_value") else dim.dim_param or None
                    for dim in item.type.tensor_type.shape.dim
                ],
            }
            for item in model.graph.output
        ]
        result["class_count_is_nine"] = any(9 in output["shape"] for output in result["outputs"])
    except Exception as exc:
        result.update({"inspection_status": "INSPECTION_FAILED", "error_category": type(exc).__name__})
    return result


def crosscheck_receipts(
    checkpoints: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    actual_hashes: dict[str, str],
) -> dict[str, Any]:
    candidate_hashes = {item["sha256"] for item in checkpoints}
    all_refs = set().union(*(referenced_hashes(item.get("content")) for item in documents))
    targets = {
        "dev_logits": "dev_logits.npz",
        "calibration_logits": "calibration_logits.npz",
        "provisional_test_logits": "provisional_test_logits.npz",
        "provisional_test_results": "provisional_test",
        "onnx_model": ".onnx",
    }
    links: dict[str, Any] = {}
    for label, marker in targets.items():
        matching_documents = []
        referenced_candidates: set[str] = set()
        for document in documents:
            flattened = list(flatten_strings(document.get("content")))
            if any(marker in text.lower() for _, text in flattened):
                matching_documents.append(document["path"])
                referenced_candidates |= referenced_hashes(document.get("content")) & candidate_hashes
        links[label] = {
            "metadata_documents": matching_documents,
            "candidate_checkpoint_hashes": sorted(referenced_candidates),
            "exactly_one_checkpoint_proven": len(referenced_candidates) == 1,
        }
    return {
        "candidate_checkpoint_hashes": sorted(candidate_hashes),
        "metadata_documents_checked": [item["path"] for item in documents],
        "artifact_checkpoint_links": links,
        "checkpoint_hashes_referenced": sorted(candidate_hashes & all_refs),
        "unreferenced_checkpoint_candidates": sorted(candidate_hashes - all_refs),
        "referenced_hashes_missing_from_audit_files": sorted(all_refs - set(actual_hashes.values())),
        "all_referenced_local_hashes_match": all(
            reference in actual_hashes.values() for reference in all_refs
        ),
    }


def decide(
    checkpoint_rows: list[dict[str, Any]],
    mappings: list[list[str]],
    baseline_metadata: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    temperatures: list[Path],
    thresholds: list[Path],
    onnx_rows: list[dict[str, Any]],
    crosscheck: dict[str, Any],
) -> dict[str, Any]:
    actions: list[str] = []
    checkpoint_hashes = {row["sha256"] for row in checkpoint_rows}
    mapping_consistent = bool(mappings) and all(mapping == EXPECTED_CLASSES for mapping in mappings)
    links = crosscheck["artifact_checkpoint_links"]
    required_origins = ("dev_logits", "calibration_logits", "provisional_test_logits", "onnx_model")
    exact_checkpoint_link = all(links[name]["exactly_one_checkpoint_proven"] for name in required_origins)
    linked_hashes = {
        links[name]["candidate_checkpoint_hashes"][0]
        for name in required_origins
        if links[name]["exactly_one_checkpoint_proven"]
    }
    exact_checkpoint_link = exact_checkpoint_link and len(linked_hashes) == 1
    onnx_ok = any(
        row.get("inspection_status") == "INSPECTED"
        and row.get("class_count_is_nine")
        and any(item["version"] == 17 for item in row.get("opsets", []))
        for row in onnx_rows
    )
    preprocessing_proven = any(
        any("preprocess" in key.lower() or "image_size" in key.lower() for key, _ in flatten_strings(item.get("content")))
        for item in baseline_metadata + receipts
    )
    if not mapping_consistent:
        actions.append("Prove one identical ordered nine-class mapping across checkpoint, exports, receipts, and ONNX.")
    if not exact_checkpoint_link:
        actions.append("Resolve which of the two checkpoint hashes generated each export and receipt.")
    if not preprocessing_proven:
        actions.append("Recover the exact runtime preprocessing configuration.")
    if not onnx_ok:
        actions.append("Prove ONNX opset/output metadata or re-export from the proven checkpoint.")
    if not temperatures:
        actions.append("Locate a frozen standalone temperature artifact or recalibrate from the untouched calibration split.")
    if not thresholds:
        actions.append("Locate frozen pre-test thresholds/abstention or reconstruct only from calibration evidence.")

    lineage_proven = mapping_consistent and exact_checkpoint_link and preprocessing_proven
    if not lineage_proven:
        primary = "LINEAGE_AMBIGUOUS"
    elif not onnx_ok:
        primary = "REQUIRES_ONNX_REEXPORT"
    elif not temperatures:
        primary = "READY_FOR_RECALIBRATION_FROM_EXISTING_CALIBRATION_SPLIT"
    elif not thresholds:
        primary = "READY_FOR_THRESHOLD_RECONSTRUCTION_FROM_EXISTING_CALIBRATION_SPLIT"
    else:
        primary = "READY_FOR_RUNTIME_RECONSTRUCTION"
    assert primary in VALID_DECISIONS
    return {
        "primary_decision": primary,
        "required_actions": actions,
        "lineage_proven": lineage_proven,
        "class_mapping_consistent": mapping_consistent,
        "exact_checkpoint_origin_proven": exact_checkpoint_link,
        "preprocessing_proven": preprocessing_proven,
        "onnx_ready_for_parity": lineage_proven and onnx_ok,
        "provisional_results_used_for_selection_or_tuning": False,
        "provisional_test_images_opened": False,
        "training_or_model_modification_performed": False,
    }


def run(audit_path: Path, output_dir: Path) -> dict[str, Any]:
    audit = load_json(audit_path)
    paths = artifact_paths(audit)
    actual_hashes = {str(path): sha256(path) for path in paths}
    checkpoint_paths = [path for path in paths if path.suffix.lower() in MODEL_SUFFIXES]
    checkpoint_rows = [checkpoint_metadata(path) for path in checkpoint_paths]

    baseline_metadata = json_evidence(paths, "baseline_export_metadata.json")
    receipts = json_evidence(paths, "one_time_evaluation_receipt.json")
    provisional_metrics = json_evidence(paths, "provisional_test_metrics.json")
    lineage_docs = lineage_documents(paths)
    class_mapping_files = [
        path for path in paths
        if path.name.lower() in {"class_to_index.json", "class_mapping.json", "class_mappings.json"}
    ]
    mappings = []
    for path in class_mapping_files:
        try:
            mapping = class_mapping_from(load_json(path))
            if mapping:
                mappings.append(mapping)
        except Exception:
            pass
    mappings.extend(
        row["class_mapping"] for row in checkpoint_rows if row.get("class_mapping")
    )

    temperature_paths = [
        path for path in paths
        if "temperature" in path.name.lower() and path.suffix.lower() == ".json"
    ]
    threshold_paths = [
        path for path in paths
        if any(term in path.name.lower() for term in ("threshold", "abstention"))
        and path.suffix.lower() in {".json", ".csv"}
        and "provisional_test" not in str(path).lower()
    ]
    calibration_npz = [
        inspect_npz_metadata(path) for path in paths
        if path.name.lower() in {"dev_logits.npz", "calibration_logits.npz"}
    ]
    onnx_rows = [inspect_onnx(path) for path in paths if path.suffix.lower() == ".onnx"]
    receipt_check = crosscheck_receipts(
        checkpoint_rows, lineage_docs, actual_hashes
    )
    decision = decide(
        checkpoint_rows, mappings, baseline_metadata, receipts,
        temperature_paths, threshold_paths, onnx_rows, receipt_check,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    comparison = {
        "candidates": checkpoint_rows,
        "candidate_hashes_differ": len({row["sha256"] for row in checkpoint_rows}) > 1,
    }
    calibration_inventory = {
        "development_and_calibration_array_metadata": calibration_npz,
        "standalone_temperature_artifacts": [
            {"path": str(path), "sha256": actual_hashes[str(path)]} for path in temperature_paths
        ],
        "standalone_pretest_threshold_or_abstention_artifacts": [
            {"path": str(path), "sha256": actual_hashes[str(path)]} for path in threshold_paths
        ],
        "reconstruction_performed": False,
    }
    onnx_report = {
        "candidates": onnx_rows,
        "parity_executed": False,
        "parity_block_reason": (
            None if decision["onnx_ready_for_parity"]
            else "Exact checkpoint origin and preprocessing are not both proven."
        ),
    }
    lineage = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_audit": str(audit_path),
        "source_audit_sha256": sha256(audit_path),
        "files_crosschecked": len(paths),
        "checkpoint_comparison": comparison,
        "class_mappings_found": mappings,
        "class_mapping_expected": EXPECTED_CLASSES,
        "baseline_export_metadata": baseline_metadata,
        "one_time_evaluation_receipts": receipts,
        "historical_provisional_metrics": provisional_metrics,
        "historical_provisional_metrics_policy": (
            "Recorded only; not used for model selection, calibration, thresholding, or tuning."
        ),
        "receipt_crosscheck": receipt_check,
        "calibration_inventory": calibration_inventory,
        "onnx_lineage": onnx_report,
        "decision": decision,
    }
    write_json(output_dir / "checkpoint_comparison.json", comparison)
    write_json(output_dir / "receipt_crosscheck.json", receipt_check)
    write_json(output_dir / "calibration_artifact_inventory.json", calibration_inventory)
    write_json(output_dir / "onnx_lineage_report.json", onnx_report)
    write_json(output_dir / "recovery_decision.json", decision)
    write_json(output_dir / "legacy_joint_lineage_report.json", lineage)
    markdown = [
        "# Legacy Joint Model Recovery Audit",
        "",
        f"Primary decision: **{decision['primary_decision']}**",
        "",
        f"Checkpoint candidates inspected: {len(checkpoint_rows)}",
        f"Files cross-checked: {len(paths)}",
        f"Class mapping consistent: {decision['class_mapping_consistent']}",
        f"Exact checkpoint origin proven: {decision['exact_checkpoint_origin_proven']}",
        f"Preprocessing proven: {decision['preprocessing_proven']}",
        "",
        "Provisional-test metrics were recorded as historical evidence only. They were not used for selection, tuning, recalibration, or threshold modification. No provisional-test images were opened.",
        "",
        "## Required actions",
        *[f"- {action}" for action in decision["required_actions"]],
    ]
    (output_dir / "legacy_joint_lineage_report.md").write_text(
        "\n".join(markdown) + "\n", encoding="utf-8"
    )
    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audit-report",
        default="/content/drive/MyDrive/AgrowAI_V1/audits/multi_crop_legacy_audit/legacy_joint_artifact_audit.json",
    )
    parser.add_argument(
        "--output-dir",
        default="/content/drive/MyDrive/AgrowAI_V1/audits/legacy_joint_recovery",
    )
    args = parser.parse_args()
    decision = run(Path(args.audit_report), Path(args.output_dir))
    print(f"PRIMARY_DECISION={decision['primary_decision']}")
    print("AGROWAI_LEGACY_JOINT_RECOVERY_AUDIT_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
