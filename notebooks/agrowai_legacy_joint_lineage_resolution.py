"""Narrow, read-only lineage resolver for the legacy nine-class AgrowAI model."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DRIVE_ROOT = Path("/content/drive/MyDrive/AgrowAI_V1")
ALLOWED_ROOTS = (
    DRIVE_ROOT / "checkpoints/mobilenetv3_small_v1",
    DRIVE_ROOT / "outputs/mobilenetv3_small_v1",
    DRIVE_ROOT / "exports/mobilenetv3_small_v1",
    DRIVE_ROOT / "provisional_test_results/mobilenetv3_small_v1",
)
ALLOWED_SINGLE_FILES = (DRIVE_ROOT / "outputs/v1_split_manifest.json",)
LEGACY_ONNX = DRIVE_ROOT / "exports/mobilenetv3_small_v1/agrowai_v1_classifier.onnx"
TARGET_CHECKPOINT_SHA256 = "f9719d48d3a8d274d039f0bd36d78cc5fa1282a8f15b2f471ab27d5c043e8117"
EXPECTED_DEV_SHA256 = "3a4943304816686b6721bc69f5c202d5705b3898e11cb648b3b2ad4471e6ce46"
EXPECTED_CALIBRATION_SHA256 = "d9981a2235a843be375d65e2b713225df6aad4e22870153f0a0ed4df8be77e9f"
EXPECTED_MANIFEST_SHA256 = "482cf5f9144cc0563e4e85d2bb3a9cb0e901896edf6bcae2d949dadfa65c232f"
EXPECTED_MAPPING_SHA256 = "639d3615eb166f860221a2290ba87dabcca814ba74723315422e5a567388cc29"
HISTORICAL_TEMPERATURE = 1.1593322394366143
HISTORICAL_CONFIDENCE_THRESHOLD = 0.8
HISTORICAL_MARGIN_THRESHOLD = 0.0
EXPECTED_CLASSES = [
    "cotton_fusarium_wilt", "cotton_healthy", "cotton_verticillium_wilt",
    "groundnut_healthy", "groundnut_rust", "paddy_healthy", "rice_blast",
    "rice_brown_leaf_spot", "rice_tungro",
]
EXCLUDED_TERMS = (
    "banana", "healthy_gate", "disease_classifier", "external_benchmark", "quarantine"
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VALID_DECISIONS = {
    "READY_FOR_RUNTIME_RECONSTRUCTION",
    "READY_FOR_RECALIBRATION_FROM_EXISTING_CALIBRATION_SPLIT",
    "READY_FOR_THRESHOLD_RECONSTRUCTION_FROM_EXISTING_CALIBRATION_SPLIT",
    "REQUIRES_ONNX_REEXPORT",
    "REQUIRES_RETRAINING",
    "LINEAGE_AMBIGUOUS",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def excluded(path: Path) -> bool:
    lowered = str(path).lower()
    return any(term in lowered for term in EXCLUDED_TERMS)


def discover() -> list[Path]:
    files: list[Path] = []
    for root in ALLOWED_ROOTS:
        if root.is_dir():
            files.extend(path for path in root.rglob("*") if path.is_file() and not excluded(path))
    files.extend(path for path in ALLOWED_SINGLE_FILES if path.is_file() and not excluded(path))
    return sorted(set(files), key=lambda path: str(path).lower())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def flatten(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(item, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from flatten(item, f"{prefix}[{index}]")
    else:
        yield prefix, value


def hashes_in(value: Any) -> set[str]:
    found = set()
    for _, item in flatten(value):
        text = str(item).lower()
        if len(text) == 64 and all(char in "0123456789abcdef" for char in text):
            found.add(text)
    return found


def mapping_from(value: Any) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    if not isinstance(value, dict):
        return None
    for key in ("class_to_index", "class_mapping", "classes", "class_names", "idx_to_class"):
        candidate = value.get(key)
        if isinstance(candidate, list) and all(isinstance(item, str) for item in candidate):
            return list(candidate)
        if isinstance(candidate, dict):
            if all(isinstance(index, int) for index in candidate.values()):
                return [name for name, _ in sorted(candidate.items(), key=lambda item: item[1])]
            if candidate and all(str(index).isdigit() for index in candidate):
                return [str(name) for index, name in sorted(candidate.items(), key=lambda item: int(item[0]))]
    for item in value.values():
        result = mapping_from(item)
        if result:
            return result
    return None


def state_dict_from(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    for key in ("model", "model_state_dict", "state_dict"):
        if isinstance(value.get(key), dict):
            return value[key]
    if value and all(hasattr(item, "shape") for item in value.values()):
        return value
    return None


def inspect_checkpoint(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size,
        "map_location": "cpu", "weights_only": True,
    }
    try:
        import torch

        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as exc:
        result.update({"inspection_status": "SAFE_LOAD_FAILED", "error_category": type(exc).__name__})
        return result
    result["inspection_status"] = "INSPECTED"
    if isinstance(checkpoint, dict):
        result["checkpoint_keys"] = sorted(str(key) for key in checkpoint)
        mapping = mapping_from(checkpoint)
        result["embedded_ordered_mapping"] = mapping
        result["embedded_mapping_matches_expected"] = mapping == EXPECTED_CLASSES
        for key in ("epoch", "architecture", "arch", "model_name", "model_version",
                    "metrics", "config", "cfg", "training_config"):
            if key in checkpoint:
                value = checkpoint[key]
                result[key] = value if isinstance(value, (str, int, float, bool, list, dict, type(None))) else str(type(value))
    state = state_dict_from(checkpoint)
    dimensions = {}
    if state:
        for key, tensor in state.items():
            shape = getattr(tensor, "shape", None)
            if shape is not None:
                dimensions[str(key)] = [int(part) for part in shape]
    result["state_tensor_dimensions"] = dimensions
    result["nine_class_output_tensors"] = [
        {"key": key, "shape": shape}
        for key, shape in dimensions.items()
        if len(shape) in (1, 2) and 9 in shape
    ]
    result["output_dimension_is_nine"] = bool(result["nine_class_output_tensors"])
    return result


def inspect_npz(path: Path) -> dict[str, Any]:
    result = {"path": str(path), "sha256": sha256(path)}
    try:
        import numpy as np

        with np.load(path, allow_pickle=False) as arrays:
            result["arrays"] = {
                key: {"shape": list(arrays[key].shape), "dtype": str(arrays[key].dtype)}
                for key in arrays.files
            }
    except Exception as exc:
        result["error_category"] = type(exc).__name__
    return result


def inspect_onnx(path: Path) -> dict[str, Any]:
    result = {
        "path": str(path), "exists": path.is_file(),
        "parity_executed": False,
    }
    if not path.is_file():
        return result
    result.update({"sha256": sha256(path), "size_bytes": path.stat().st_size})
    try:
        import onnx

        model = onnx.load(str(path), load_external_data=False)
        result["inspection_status"] = "INSPECTED"
        result["opsets"] = [
            {"domain": item.domain or "ai.onnx", "version": int(item.version)}
            for item in model.opset_import
        ]
        def tensor_rows(items: Any) -> list[dict[str, Any]]:
            return [{
                "name": item.name,
                "shape": [
                    dim.dim_value if dim.HasField("dim_value") else dim.dim_param or None
                    for dim in item.type.tensor_type.shape.dim
                ],
            } for item in items]
        result["inputs"] = tensor_rows(model.graph.input)
        result["outputs"] = tensor_rows(model.graph.output)
        result["output_class_count_is_nine"] = any(9 in row["shape"] for row in result["outputs"])
    except Exception as exc:
        result.update({"inspection_status": "INSPECTION_FAILED", "error_category": type(exc).__name__})
    return result


def verify_recorded_hashes(document: dict[str, Any], files: list[Path]) -> dict[str, Any]:
    actual_by_name: dict[str, list[dict[str, str]]] = {}
    for path in files:
        actual_by_name.setdefault(path.name.lower(), []).append({"path": str(path), "sha256": sha256(path)})
    checks = []
    for field, value in flatten(document):
        text = str(value).lower()
        if len(text) != 64 or not all(char in "0123456789abcdef" for char in text):
            continue
        filename = next(
            (str(other).lower() for other_field, other in flatten(document)
             if other_field.rsplit(".", 1)[0] == field.rsplit(".", 1)[0]
             and isinstance(other, str) and "." in other),
            None,
        )
        candidates = actual_by_name.get(Path(filename).name.lower(), []) if filename else []
        checks.append({
            "field": field, "recorded_sha256": text, "associated_filename": filename,
            "candidate_files": candidates,
            "verified": any(item["sha256"] == text for item in candidates),
        })
    return {"checks": checks, "all_associated_hashes_verified": bool(checks) and all(row["verified"] for row in checks)}


def verify_result_receipt(receipt: dict[str, Any], files: list[Path]) -> dict[str, Any]:
    """Hash result files only. Image files are categorically excluded."""
    allowed_files = [path for path in files if path.suffix.lower() not in IMAGE_SUFFIXES]
    known_hashes = {sha256(path): str(path) for path in allowed_files}
    recorded = hashes_in(receipt)
    return {
        "recorded_hashes": sorted(recorded),
        "verified_result_hashes": {
            value: known_hashes[value] for value in sorted(recorded) if value in known_hashes
        },
        "unresolved_recorded_hashes": sorted(recorded - set(known_hashes)),
        "image_files_opened": False,
    }


def mapping_verification(files: list[Path], documents: list[dict[str, Any]]) -> dict[str, Any]:
    mapping_files = [
        path for path in files
        if path.name.lower() in {"class_to_index.json", "class_mapping.json", "class_mappings.json"}
    ]
    rows = []
    for path in mapping_files:
        try:
            value = load_json(path)
            rows.append({
                "path": str(path), "file_sha256": sha256(path),
                "ordered_mapping": mapping_from(value),
                "matches_expected_order": mapping_from(value) == EXPECTED_CLASSES,
                "matches_receipt_sha256": sha256(path) == EXPECTED_MAPPING_SHA256,
            })
        except Exception as exc:
            rows.append({"path": str(path), "error_category": type(exc).__name__})
    canonical_object = {name: index for index, name in enumerate(EXPECTED_CLASSES)}
    serializations = {
        "compact_insertion_order": json.dumps(canonical_object, separators=(",", ":")).encode(),
        "compact_sorted_keys": json.dumps(canonical_object, separators=(",", ":"), sort_keys=True).encode(),
        "pretty_insertion_order_newline": (json.dumps(canonical_object, indent=2) + "\n").encode(),
    }
    computed = {name: hashlib.sha256(value).hexdigest() for name, value in serializations.items()}
    return {
        "expected_order": EXPECTED_CLASSES,
        "mapping_files": rows,
        "candidate_serialization_hashes": computed,
        "receipt_hash": EXPECTED_MAPPING_SHA256,
        "exact_file_hash_match_found": any(row.get("matches_receipt_sha256") for row in rows),
        "canonical_serialization_match_found": EXPECTED_MAPPING_SHA256 in computed.values(),
        "document_mapping_matches": [
            mapping_from(document) == EXPECTED_CLASSES for document in documents if mapping_from(document)
        ],
    }


def make_decision(
    target_checkpoint_found: bool,
    dev_linked: bool,
    calibration_linked: bool,
    receipt_linked: bool,
    runtime_linked: bool,
    mapping_ok: bool,
    onnx_origin_proven: bool,
    onnx_metadata_ok: bool,
    standalone_temperature: bool,
    standalone_thresholds: bool,
) -> dict[str, Any]:
    checkpoint_lineage_proven = all((
        target_checkpoint_found, dev_linked, calibration_linked,
        receipt_linked, runtime_linked, mapping_ok,
    ))
    if not checkpoint_lineage_proven:
        primary = "LINEAGE_AMBIGUOUS"
    elif not onnx_origin_proven or not onnx_metadata_ok:
        primary = "REQUIRES_ONNX_REEXPORT"
    elif not standalone_temperature:
        primary = "READY_FOR_RECALIBRATION_FROM_EXISTING_CALIBRATION_SPLIT"
    elif not standalone_thresholds:
        primary = "READY_FOR_THRESHOLD_RECONSTRUCTION_FROM_EXISTING_CALIBRATION_SPLIT"
    else:
        primary = "READY_FOR_RUNTIME_RECONSTRUCTION"
    assert primary in VALID_DECISIONS
    return {
        "primary_decision": primary,
        "checkpoint_lineage_proven": checkpoint_lineage_proven,
        "target_checkpoint_found": target_checkpoint_found,
        "dev_logits_linked": dev_linked,
        "calibration_logits_linked": calibration_linked,
        "provisional_receipt_linked": receipt_linked,
        "runtime_snapshot_linked": runtime_linked,
        "ordered_mapping_verified": mapping_ok,
        "onnx_origin_proven": onnx_origin_proven,
        "onnx_metadata_ok": onnx_metadata_ok,
        "temperature_reconstruction_performed": False,
        "threshold_reconstruction_performed": False,
        "provisional_outputs_used_for_tuning": False,
        "provisional_test_images_opened": False,
    }


def run(output_dir: Path) -> dict[str, Any]:
    files = discover()
    json_documents = []
    for path in files:
        if path.suffix.lower() == ".json":
            try:
                json_documents.append({"path": str(path), "content": load_json(path)})
            except Exception:
                pass
    checkpoint_paths = [path for path in files if path.suffix.lower() in {".pt", ".pth"}]
    checkpoint_rows = [inspect_checkpoint(path) for path in checkpoint_paths]
    target_rows = [row for row in checkpoint_rows if row["sha256"] == TARGET_CHECKPOINT_SHA256]

    dev_paths = [path for path in files if path.name.lower() == "dev_logits.npz"]
    calibration_paths = [path for path in files if path.name.lower() == "calibration_logits.npz"]
    dev_rows = [inspect_npz(path) for path in dev_paths]
    calibration_rows = [inspect_npz(path) for path in calibration_paths]
    baseline_docs = [row for row in json_documents if Path(row["path"]).name.lower() == "baseline_export_metadata.json"]
    receipt_docs = [row for row in json_documents if Path(row["path"]).name.lower() == "one_time_evaluation_receipt.json"]
    runtime_docs = [row for row in json_documents if Path(row["path"]).name.lower() == "runtime_training_config_snapshot.json"]
    all_document_values = [row["content"] for row in json_documents]

    mapping_report = mapping_verification(files, all_document_values)
    checkpoint_report = {
        "allowed_roots": [str(path) for path in ALLOWED_ROOTS],
        "excluded_terms": list(EXCLUDED_TERMS),
        "candidate_checkpoints": checkpoint_rows,
        "target_sha256": TARGET_CHECKPOINT_SHA256,
        "target_checkpoint_matches": target_rows,
        "outputs_candidate_exists": any(
            str(path).replace("\\", "/").endswith("/outputs/mobilenetv3_small_v1/best.pt")
            for path in checkpoint_paths
        ),
        "non_target_checkpoint_candidates": [
            row for row in checkpoint_rows if row["sha256"] != TARGET_CHECKPOINT_SHA256
        ],
    }
    export_report = {
        "dev_logits": dev_rows,
        "calibration_logits": calibration_rows,
        "dev_expected_sha256": EXPECTED_DEV_SHA256,
        "calibration_expected_sha256": EXPECTED_CALIBRATION_SHA256,
        "dev_hash_verified": any(row["sha256"] == EXPECTED_DEV_SHA256 for row in dev_rows),
        "calibration_hash_verified": any(row["sha256"] == EXPECTED_CALIBRATION_SHA256 for row in calibration_rows),
        "dev_shape_verified": any(
            any(array.get("shape") == [1320, 9] for array in row.get("arrays", {}).values())
            for row in dev_rows
        ),
        "calibration_shape_verified": any(
            any(array.get("shape") == [660, 9] for array in row.get("arrays", {}).values())
            for row in calibration_rows
        ),
        "baseline_export_metadata_hash_checks": [
            {"path": row["path"], **verify_recorded_hashes(row["content"], files)}
            for row in baseline_docs
        ],
    }
    receipt_report = {
        "historical_temperature": HISTORICAL_TEMPERATURE,
        "historical_confidence_threshold": HISTORICAL_CONFIDENCE_THRESHOLD,
        "historical_margin_threshold": HISTORICAL_MARGIN_THRESHOLD,
        "historical_values_used_for_tuning": False,
        "receipts": [
            {"path": row["path"], **verify_result_receipt(row["content"], files)}
            for row in receipt_docs
        ],
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "expected_mapping_sha256": EXPECTED_MAPPING_SHA256,
    }
    onnx_report = inspect_onnx(LEGACY_ONNX)

    def any_doc_links(rows: list[dict[str, Any]], *hashes: str) -> bool:
        return any(set(hashes).issubset(hashes_in(row["content"])) for row in rows)

    mapping_ok = (
        mapping_report["exact_file_hash_match_found"]
        and any(row.get("matches_expected_order") for row in mapping_report["mapping_files"])
    )
    target_found = bool(target_rows) and any(
        row.get("output_dimension_is_nine") for row in target_rows
    )
    dev_linked = (
        export_report["dev_hash_verified"]
        and export_report["dev_shape_verified"]
        and any_doc_links(baseline_docs, TARGET_CHECKPOINT_SHA256, EXPECTED_DEV_SHA256)
    )
    calibration_linked = (
        export_report["calibration_hash_verified"]
        and export_report["calibration_shape_verified"]
        and any_doc_links(baseline_docs, TARGET_CHECKPOINT_SHA256, EXPECTED_CALIBRATION_SHA256)
    )
    receipt_linked = any_doc_links(
        receipt_docs, TARGET_CHECKPOINT_SHA256, EXPECTED_MANIFEST_SHA256, EXPECTED_MAPPING_SHA256
    )
    runtime_linked = any_doc_links(runtime_docs, TARGET_CHECKPOINT_SHA256, EXPECTED_MANIFEST_SHA256)
    onnx_origin_proven = any_doc_links(
        json_documents, TARGET_CHECKPOINT_SHA256, onnx_report.get("sha256", "missing")
    )
    onnx_metadata_ok = bool(
        onnx_report.get("output_class_count_is_nine")
        and any(item["version"] == 17 for item in onnx_report.get("opsets", []))
    )
    standalone_temperature = any(
        "temperature" in path.name.lower() and "provisional" not in str(path).lower()
        for path in files
    )
    standalone_thresholds = any(
        any(term in path.name.lower() for term in ("threshold", "abstention"))
        and "provisional" not in str(path).lower()
        for path in files
    )
    decision = make_decision(
        target_found, dev_linked, calibration_linked, receipt_linked, runtime_linked,
        mapping_ok, onnx_origin_proven, onnx_metadata_ok,
        standalone_temperature, standalone_thresholds,
    )
    decision["calibration_temperature_reconstructable_without_provisional_outputs"] = bool(
        target_found and calibration_linked and calibration_rows
    )
    decision["thresholds_require_calibration_only_reconstruction"] = bool(
        decision["calibration_temperature_reconstructable_without_provisional_outputs"]
        and not standalone_thresholds
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "legacy_checkpoint_resolution.json", checkpoint_report)
    write_json(output_dir / "legacy_export_hash_verification.json", export_report)
    write_json(output_dir / "legacy_class_mapping_verification.json", mapping_report)
    write_json(output_dir / "legacy_onnx_inspection.json", onnx_report)
    write_json(output_dir / "legacy_receipt_verification.json", receipt_report)
    write_json(output_dir / "legacy_lineage_resolution_decision.json", decision)
    report = [
        "# Legacy Joint Model Lineage Resolution",
        "",
        f"Primary decision: **{decision['primary_decision']}**",
        "",
        f"Target checkpoint found: {decision['target_checkpoint_found']}",
        f"Development export linked: {decision['dev_logits_linked']}",
        f"Calibration export linked: {decision['calibration_logits_linked']}",
        f"Provisional receipt linked: {decision['provisional_receipt_linked']}",
        f"Runtime snapshot linked: {decision['runtime_snapshot_linked']}",
        f"Ordered mapping verified: {decision['ordered_mapping_verified']}",
        f"ONNX origin proven: {decision['onnx_origin_proven']}",
        "",
        "The provisional receipt and result hashes were inspected only as historical lineage evidence. No provisional image was opened and no provisional result was used for model selection, calibration, or threshold tuning.",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
    ]
    (output_dir / "legacy_lineage_resolution_report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="/content/drive/MyDrive/AgrowAI_V1/audits/legacy_joint_lineage_resolution",
    )
    args = parser.parse_args()
    decision = run(Path(args.output_dir))
    print(f"PRIMARY_DECISION={decision['primary_decision']}")
    print("AGROWAI_LEGACY_JOINT_LINEAGE_RESOLUTION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
