"""Build the four-crop metadata audit without opening reserved images."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
STAMP = "20260728T192520Z"
OUT = PROJECT / "docs/model_audits/four_crop_identification" / STAMP
MANIFEST = Path(r"D:\AgrowAI\model_exports\crop_identification\split_manifest.csv")
REGISTRY = Path(r"D:\AgrowAI\model_exports\crop_identification\dataset_registry.json")
TARGETS = ("banana", "paddy", "cotton", "groundnut")


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=False)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    with MANIFEST.open(newline="", encoding="utf-8-sig") as stream:
        source_rows = [
            row for row in csv.DictReader(stream) if row["crop_class"] in TARGETS
        ]

    sources_by_id = {
        source["dataset_id"]: source
        for source in registry["sources"]
        if source["crop"] in TARGETS
    }
    inventory: list[dict[str, object]] = []
    excluded: list[dict[str, str]] = []
    family_crops: dict[str, set[str]] = defaultdict(set)
    family_splits: dict[str, set[str]] = defaultdict(set)
    family_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    sha_rows: dict[str, list[dict[str, str]]] = defaultdict(list)

    for index, row in enumerate(source_rows, 1):
        source = sources_by_id[row["source_dataset"]]
        reserved_calibration = row["split"] == "calibration"
        reserved_provisional = row["split"] == "provisional_test"
        reasons = []
        if row["verification_status"] != "VERIFIED_USABLE":
            reasons.append("SOURCE_FAMILY_UNRESOLVED")
        if reserved_calibration:
            reasons.append("CALIBRATION_RESERVED")
        if reserved_provisional:
            reasons.append("PROVISIONAL_TEST_RESERVED")
        if row["original_or_augmented"] != "ORIGINAL":
            reasons.append("AUGMENTED_ONLY")
        if row["licence_status"] != "VERIFIED_CC_BY_4_0":
            reasons.append("LICENCE_UNKNOWN")
        training_eligible = not reasons
        item = {
            "image_id": f"crop-id-{index:06d}",
            "absolute_or_project_relative_path": row["image_path"],
            "sha256": row["image_sha256"],
            "crop_class": row["crop_class"],
            "source_dataset": row["source_dataset"],
            "source_reference": source["source_url"],
            "licence": source["licence"],
            "original_or_augmented": row["original_or_augmented"],
            "original_source_family": row["duplicate_family"],
            "existing_split": row["split"],
            "disease_class": row["source_class"],
            "crop_identity_evidence": (
                "Verified single-crop parent dataset; independent source-family "
                "and shortcut review remains pending."
            ),
            "licence_verified": row["licence_status"] == "VERIFIED_CC_BY_4_0",
            "crop_identity_verified": False,
            "is_calibration_image": reserved_calibration,
            "is_provisional_test_image": reserved_provisional,
            "is_sealed_evaluation_image": reserved_provisional,
            "is_augmented": row["original_or_augmented"] != "ORIGINAL",
            "training_eligible": training_eligible,
            "exclusion_reasons": reasons,
        }
        inventory.append(item)
        if reasons:
            excluded.append(
                {
                    "image_id": str(item["image_id"]),
                    "path": row["image_path"],
                    "crop_class": row["crop_class"],
                    "split": row["split"],
                    "reasons": "|".join(reasons),
                }
            )
        family = row["duplicate_family"]
        family_crops[family].add(row["crop_class"])
        family_splits[family].add(row["split"])
        family_rows[family].append(row)
        sha_rows[row["image_sha256"]].append(row)

    dump(OUT / "IMAGE_INVENTORY.json", inventory)
    with (OUT / "IMAGE_INVENTORY.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = [
            "image_id", "absolute_or_project_relative_path", "sha256", "crop_class",
            "source_dataset", "source_reference", "licence", "original_or_augmented",
            "original_source_family", "existing_split", "disease_class",
            "crop_identity_evidence", "licence_verified", "crop_identity_verified",
            "is_calibration_image", "is_provisional_test_image",
            "is_sealed_evaluation_image", "is_augmented", "training_eligible",
            "exclusion_reasons",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in inventory:
            writer.writerow({**row, "exclusion_reasons": "|".join(row["exclusion_reasons"])})
    with (OUT / "EXCLUDED_IMAGES.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["image_id", "path", "crop_class", "split", "reasons"]
        )
        writer.writeheader()
        writer.writerows(excluded)

    family_records = []
    for family, rows in sorted(family_rows.items()):
        family_records.append(
            {
                "duplicate_family_id": family,
                "image_count": len(rows),
                "crops": "|".join(sorted(family_crops[family])),
                "splits": "|".join(sorted(family_splits[family])),
                "cross_class": len(family_crops[family]) > 1,
                "cross_split": len(family_splits[family]) > 1,
            }
        )
    with (OUT / "DUPLICATE_FAMILIES.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=family_records[0].keys())
        writer.writeheader()
        writer.writerows(family_records)
    conflicts = [row for row in family_records if row["cross_class"]]
    with (OUT / "CROSS_CLASS_CONFLICTS.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=family_records[0].keys())
        writer.writeheader()
        writer.writerows(conflicts)

    eligible = Counter(
        str(row["crop_class"]) for row in inventory if bool(row["training_eligible"])
    )
    split_counts = Counter((row["crop_class"], row["existing_split"]) for row in inventory)
    exact_duplicate_groups = sum(1 for rows in sha_rows.values() if len(rows) > 1)
    cross_split_families = sum(1 for splits in family_splits.values() if len(splits) > 1)
    duplicate_audit = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_manifest": str(MANIFEST),
        "source_manifest_sha256": sha256(MANIFEST),
        "rows_audited": len(inventory),
        "unique_sha256": len(sha_rows),
        "exact_duplicate_groups": exact_duplicate_groups,
        "duplicate_families": len(family_rows),
        "cross_class_duplicate_families": len(conflicts),
        "duplicate_families_crossing_existing_splits": cross_split_families,
        "perceptual_family_source": "Existing audited duplicate_family metadata",
        "reserved_images_opened": False,
        "passed": exact_duplicate_groups == 0 and not conflicts and cross_split_families == 0,
    }
    dump(OUT / "DUPLICATE_AUDIT.json", duplicate_audit)

    dataset_sources = []
    for crop in TARGETS:
        source = next(item for item in sources_by_id.values() if item["crop"] == crop)
        dataset_sources.append(
            {
                "dataset_id": source["dataset_id"],
                "crop_class": crop,
                "root_path": source["extracted_root"],
                "source_name": source["dataset_name"],
                "source_reference": source["source_url"],
                "doi_or_url_reference": source["doi"],
                "licence": source["licence"],
                "archive_sha256": source["archive_sha256"],
                "original_image_count": source["candidate_image_count"],
                "augmented_image_count": 0,
                "existing_split_names": sorted(
                    {row["split"] for row in source_rows if row["crop_class"] == crop}
                ),
                "manifest_present": True,
                "hash_manifest_present": True,
                "crop_identity_reliable": True,
                "candidate_for_crop_identification": True,
                "training_eligible_count": eligible[crop],
                "notes": "Single-source shortcut and independent source-family review pending.",
            }
        )
    dump(OUT / "DATASET_SOURCES.json", dataset_sources)
    with (OUT / "SPLIT_COUNTS.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["crop_class", "existing_split", "count"])
        for (crop, split), count in sorted(split_counts.items()):
            writer.writerow([crop, split, count])

    dump(
        OUT / "SPLIT_MANIFEST.json",
        {
            "status": "NOT_CREATED",
            "reason": "DATASET_NOT_READY_FOR_TRAINING",
            "classes": list(TARGETS),
            "source_manifest_sha256": sha256(MANIFEST),
            "split_manifest_sha256": None,
            "reserved_images_opened": False,
        },
    )
    for name, status, reason in (
        ("TRAINING_RECEIPT.json", "NOT_PRODUCED", "DATASET_NOT_READY_FOR_TRAINING"),
        ("DEV_EVALUATION.json", "NOT_PERFORMED", "MODEL_NOT_TRAINED"),
        ("CALIBRATION_REPORT.json", "NOT_PERFORMED", "MODEL_NOT_TRAINED"),
        ("PROVISIONAL_TEST_RESULTS.json", "NOT_PERFORMED", "PROVISIONAL_TEST_REMAINS_SEALED"),
        ("PROVISIONAL_TEST_RECEIPT.json", "NOT_PRODUCED", "PROVISIONAL_TEST_REMAINS_SEALED"),
    ):
        dump(OUT / name, {"status": status, "reason": reason})

    summary = {
        "overall_result": "DATASET_NOT_READY_FOR_TRAINING",
        "eligible": {crop: eligible[crop] for crop in TARGETS},
        "candidate_rows": Counter(row["crop_class"] for row in inventory),
        "excluded_rows": len(excluded),
        "duplicate_audit": duplicate_audit,
        "training_ready": False,
    }
    dump(OUT / "_AUDIT_SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, default=dict))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the metadata-only four-crop identification preflight audit."
    )
    parser.parse_args()
    main()
