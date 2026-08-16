"""Validate approved inputs and build deterministic grouped four-crop splits."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

CLASSES = ("banana", "paddy", "cotton", "groundnut")
SPLITS = ("training", "development_validation", "calibration", "provisional_test")
PROPORTIONS = {
    "training": 0.70,
    "development_validation": 0.15,
    "calibration": 0.075,
    "provisional_test": 0.075,
}
SEED = 20260729


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_inputs(approval_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    required = [
        "FINAL_APPROVAL_REPORT.json",
        "IMAGE_APPROVAL_MANIFEST.json",
        "IMAGE_APPROVAL_MANIFEST.csv",
        "APPROVED_IMAGES.csv",
        "RESERVED_IMAGE_REGISTRY.json",
        "SOURCE_FAMILIES.csv",
        "FAMILY_ASSIGNMENTS.csv",
    ]
    missing = [name for name in required if not (approval_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"APPROVAL_MANIFEST_INTEGRITY_FAILURE: missing {missing}")
    report = json.loads((approval_dir / "FINAL_APPROVAL_REPORT.json").read_text(encoding="utf-8"))
    rows = json.loads((approval_dir / "IMAGE_APPROVAL_MANIFEST.json").read_text(encoding="utf-8"))
    reserved = json.loads((approval_dir / "RESERVED_IMAGE_REGISTRY.json").read_text(encoding="utf-8"))
    approved = [row for row in rows if row["approved_for_crop_identity_training"] is True]
    if len(approved) != 8246 or len(reserved) != 1460:
        raise RuntimeError("APPROVAL_MANIFEST_INTEGRITY_FAILURE: totals differ")
    counts = Counter(row["crop_class"] for row in approved)
    if counts != Counter({"banana": 762, "paddy": 6212, "cotton": 660, "groundnut": 612}):
        raise RuntimeError("APPROVAL_MANIFEST_INTEGRITY_FAILURE: crop totals differ")
    reserved_sha = {row["sha256"] for row in reserved}
    approved_sha = [row["sha256"] for row in approved]
    if len(set(approved_sha)) != len(approved_sha) or reserved_sha.intersection(approved_sha):
        raise RuntimeError("APPROVAL_MANIFEST_INTEGRITY_FAILURE: SHA overlap")
    for row in approved:
        if row["crop_class"] not in CLASSES:
            raise RuntimeError("APPROVAL_MANIFEST_INTEGRITY_FAILURE: unexpected class")
        if (
            row["reserved_for_calibration"]
            or row["reserved_for_provisional_test"]
            or row["reserved_for_sealed_evaluation"]
            or row["originality_status"] != "ORIGINAL_VERIFIED"
            or row["licence"] != "CC BY 4.0"
            or not row["source_family_id"]
            or not row["decodable"]
        ):
            raise RuntimeError("APPROVAL_MANIFEST_INTEGRITY_FAILURE: invalid approval row")
        path = Path(r"D:\AgrowAI\knowledge_base") / Path(row["path"])
        if not path.is_file():
            raise RuntimeError(f"APPROVAL_MANIFEST_INTEGRITY_FAILURE: missing {path}")
        with Image.open(path) as image:
            image.verify()
    validation = {
        "status": "PASS",
        "approval_directory": str(approval_dir),
        "approved_total": len(approved),
        "reserved_total": len(reserved),
        "approved_counts": dict(counts),
        "approved_reserved_sha_overlap": 0,
        "duplicate_approved_sha256": 0,
        "approved_paths_exist_and_decode": True,
        "reserved_images_opened": False,
        "input_hashes": {name: sha256(approval_dir / name) for name in required},
        "approval_manifest_canonical_sha256": report["approval_manifest_canonical_sha256"],
    }
    return approved, validation


def grouped_split(
    rows: list[dict[str, Any]], seed: int = SEED
) -> list[dict[str, Any]]:
    assigned: list[dict[str, Any]] = []
    for crop in CLASSES:
        crop_rows = [row for row in rows if row["crop_class"] == crop]
        families: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in crop_rows:
            families[row["source_family_id"]].append(row)
        groups = list(families.values())
        random.Random(f"{seed}:{crop}").shuffle(groups)
        targets = {split: len(crop_rows) * PROPORTIONS[split] for split in SPLITS}
        counts = Counter()
        for group in groups:
            # Allocate to the split with the greatest remaining proportional need.
            split = max(
                SPLITS,
                key=lambda name: (
                    targets[name] - counts[name],
                    -SPLITS.index(name),
                ),
            )
            for row in group:
                assigned.append({**row, "split": split})
            counts[split] += len(group)
    return sorted(assigned, key=lambda row: (row["split"], row["crop_class"], row["sha256"]))


def audit_split(rows: list[dict[str, Any]], reserved_sha: set[str]) -> dict[str, Any]:
    sha_splits: dict[str, set[str]] = defaultdict(set)
    family_splits: dict[str, set[str]] = defaultdict(set)
    sha_crops: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        sha_splits[row["sha256"]].add(row["split"])
        family_splits[row["source_family_id"]].add(row["split"])
        sha_crops[row["sha256"]].add(row["crop_class"])
    split_classes = {
        split: sorted({row["crop_class"] for row in rows if row["split"] == split})
        for split in SPLITS
    }
    result = {
        "split_integrity": "PASS",
        "rows": len(rows),
        "sha_leakage": sum(len(v) > 1 for v in sha_splits.values()),
        "family_leakage": sum(len(v) > 1 for v in family_splits.values()),
        "reserved_leakage": sum(row["sha256"] in reserved_sha for row in rows),
        "cross_class_sha_conflicts": sum(len(v) > 1 for v in sha_crops.values()),
        "all_classes_in_all_splits": all(classes == sorted(CLASSES) for classes in split_classes.values()),
        "split_classes": split_classes,
        "reserved_images_opened": False,
    }
    if any(
        [
            result["sha_leakage"],
            result["family_leakage"],
            result["reserved_leakage"],
            result["cross_class_sha_conflicts"],
            not result["all_classes_in_all_splits"],
        ]
    ):
        result["split_integrity"] = "FAIL"
    return result


def run(approval_dir: Path, dataset_dir: Path, audit_dir: Path) -> dict[str, Any]:
    audit_dir.mkdir(parents=True, exist_ok=False)
    manifests = dataset_dir / "manifests"
    reports = dataset_dir / "reports"
    manifests.mkdir(parents=True, exist_ok=False)
    reports.mkdir(parents=True, exist_ok=False)
    for split in SPLITS:
        (dataset_dir / "split_views" / split).mkdir(parents=True, exist_ok=False)

    approved, validation = validate_inputs(approval_dir)
    reserved = json.loads((approval_dir / "RESERVED_IMAGE_REGISTRY.json").read_text(encoding="utf-8"))
    reserved_sha = {row["sha256"] for row in reserved}
    assigned = grouped_split(approved)
    leakage = audit_split(assigned, reserved_sha)
    if leakage["split_integrity"] != "PASS":
        raise RuntimeError("SPLIT_INTEGRITY_FAILURE")

    source_manifest = {
        "dataset_version": "crop_identity_dataset_v1",
        "approval_source": str(approval_dir),
        "approval_manifest_canonical_sha256": validation["approval_manifest_canonical_sha256"],
        "rows": approved,
    }
    dump(manifests / "approved_source_manifest.json", source_manifest)
    split_document = {
        "dataset_version": "crop_identity_dataset_v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "random_seed": SEED,
        "classes": list(CLASSES),
        "split_names": list(SPLITS),
        "proportions": PROPORTIONS,
        "source_manifest_sha256": sha256(manifests / "approved_source_manifest.json"),
        "rows": assigned,
    }
    dump(manifests / "split_manifest.json", split_document)
    fields = [
        "image_id", "path", "sha256", "crop_class", "source_dataset",
        "source_reference", "licence", "source_family_id",
        "source_family_confidence", "split",
    ]
    with (manifests / "split_manifest.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in assigned)
    split_hash = sha256(manifests / "split_manifest.json")
    (manifests / "split_manifest.sha256").write_text(
        f"{split_hash}  split_manifest.json\n", encoding="ascii"
    )

    counts = Counter((row["split"], row["crop_class"]) for row in assigned)
    with (reports / "SPLIT_COUNTS.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["split", "crop_class", "count"])
        for split in SPLITS:
            for crop in CLASSES:
                writer.writerow([split, crop, counts[(split, crop)]])
    distribution = {
        split: {crop: counts[(split, crop)] for crop in CLASSES} for split in SPLITS
    }
    dump(reports / "SPLIT_CLASS_DISTRIBUTION.json", distribution)
    family_counts = Counter((row["split"], row["crop_class"]) for row in {
        (row["split"], row["crop_class"], row["source_family_id"]): row for row in assigned
    }.values())
    with (reports / "SPLIT_FAMILY_DISTRIBUTION.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(["split", "crop_class", "family_count"])
        for split in SPLITS:
            for crop in CLASSES:
                writer.writerow([split, crop, family_counts[(split, crop)]])
    dump(reports / "SPLIT_LEAKAGE_AUDIT.json", leakage)
    dump(audit_dir / "APPROVAL_INPUT_VALIDATION.json", validation)
    dump(audit_dir / "SPLIT_MANIFEST.json", split_document)
    for name in (
        "SPLIT_COUNTS.csv",
        "SPLIT_FAMILY_DISTRIBUTION.csv",
    ):
        (audit_dir / name).write_bytes((reports / name).read_bytes())
    dump(audit_dir / "SPLIT_CLASS_DISTRIBUTION.json", distribution)
    dump(audit_dir / "SPLIT_LEAKAGE_AUDIT.json", leakage)
    result = {
        "approval": validation,
        "split_manifest_sha256": split_hash,
        "counts": distribution,
        "leakage": leakage,
    }
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-dir", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.approval_dir.resolve(), args.dataset_dir.resolve(), args.audit_dir.resolve())


if __name__ == "__main__":
    main()
