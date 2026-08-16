from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

REQUIRED = (
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
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(source: Path, destination: Path) -> dict[str, str]:
    missing = [name for name in REQUIRED if not (source / name).is_file()]
    if missing:
        raise RuntimeError(f"RUNTIME_PACKAGE_INCOMPLETE: {missing}")
    if destination.exists():
        raise RuntimeError("RUNTIME_DESTINATION_EXISTS")
    destination.mkdir(parents=True)
    for name in REQUIRED:
        shutil.copy2(source / name, destination / name)
    runtime = {
        "crop_id": "crop_identity",
        "model_name": "crop_identity_mobilenetv3_small_v1",
        "model_version": "v1",
        "architecture": "mobilenet_v3_small",
        "classes": ["banana", "paddy", "cotton", "groundnut"],
        "field_validation_status": "PUBLIC_DATASET_PROVISIONAL",
        "official_accuracy_claim": False,
        "general_farmer_inference_authorized": False,
        "non_plant_rejection_proven": False,
    }
    (destination / "runtime_config.json").write_text(
        json.dumps(runtime, indent=2) + "\n", encoding="utf-8"
    )
    hashes = {path.name: sha256(path) for path in sorted(destination.iterdir()) if path.is_file()}
    (destination / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in hashes.items()),
        encoding="ascii",
    )
    bundle_hashes = {
        path.name: sha256(path) for path in sorted(destination.iterdir()) if path.is_file()
    }
    (destination / "DEPLOYMENT_BUNDLE_SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in bundle_hashes.items()),
        encoding="ascii",
    )
    return bundle_hashes
