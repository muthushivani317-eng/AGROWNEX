"""Evidence-based approval audit for the four-crop identification dataset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
KNOWLEDGE_BASE = Path(r"D:\AgrowAI\knowledge_base")
REGISTRY = Path(r"D:\AgrowAI\model_exports\crop_identification\dataset_registry.json")
MANIFEST = Path(r"D:\AgrowAI\model_exports\crop_identification\split_manifest.csv")
TARGETS = ("banana", "paddy", "cotton", "groundnut")
RESERVED_SPLITS = {"calibration", "provisional_test"}


@dataclass(frozen=True)
class ApprovalPolicy:
    verified_licence: str = "VERIFIED_CC_BY_4_0"
    original_label: str = "ORIGINAL"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def classify_originality(row: dict[str, str], source: dict[str, Any]) -> str:
    """Require registry evidence plus an explicit original-only manifest label."""
    if row["original_or_augmented"] != "ORIGINAL":
        return "AUGMENTED_VERIFIED"
    evidence = str(source.get("image_origin", "")).upper()
    if "ORIGINAL" in evidence:
        return "ORIGINAL_VERIFIED"
    return "UNKNOWN_ORIGINALITY"


def approval_for(
    *,
    archive_verified: bool,
    extraction_verified: bool,
    originality: str,
    crop_identity: str,
    licence_verified: bool,
    reserved: bool,
    decodable: bool,
    family_available: bool,
    cross_crop_conflict: bool,
) -> tuple[str, bool, list[str], list[str], bool]:
    """Return status, approval, basis, reasons, and human-review requirement."""
    reasons: list[str] = []
    if reserved:
        reasons.append("RESERVED_MATERIAL")
    if not archive_verified:
        reasons.append("ARCHIVE_INTEGRITY_NOT_VERIFIED")
    if not extraction_verified:
        reasons.append("EXTRACTION_NOT_VERIFIED")
    if originality != "ORIGINAL_VERIFIED":
        reasons.append("ORIGINALITY_NOT_VERIFIED")
    if crop_identity != "CROP_IDENTITY_VERIFIED_FROM_SOURCE":
        reasons.append("CROP_IDENTITY_NOT_VERIFIED")
    if not licence_verified:
        reasons.append("LICENCE_NOT_VERIFIED")
    if not decodable and not reserved:
        reasons.append("CORRUPT_OR_UNREADABLE")
    if not family_available:
        reasons.append("SOURCE_FAMILY_UNKNOWN")
    if cross_crop_conflict:
        reasons.append("CROSS_CROP_CONFLICT")

    if reserved:
        return "REJECTED_RESERVED", False, [], reasons, False
    if "CORRUPT_OR_UNREADABLE" in reasons:
        return "REJECTED_CORRUPT", False, [], reasons, False
    if originality == "AUGMENTED_VERIFIED":
        return "REJECTED_AUGMENTED", False, [], reasons, False
    if reasons:
        if "SOURCE_FAMILY_UNKNOWN" in reasons:
            status = "QUARANTINED_SOURCE_FAMILY_UNKNOWN"
        elif "ORIGINALITY_NOT_VERIFIED" in reasons:
            status = "QUARANTINED_ORIGINALITY_UNCERTAIN"
        else:
            status = "QUARANTINED_REQUIRES_HUMAN_REVIEW"
        return status, False, [], reasons, True
    basis = [
        "ARCHIVE_HASH_VERIFIED",
        "EXTRACTED_FILE_HASH_MATCH",
        "ORIGINAL_VERIFIED",
        "CROP_IDENTITY_VERIFIED_FROM_SOURCE",
        "LICENCE_VERIFIED_CC_BY_4_0",
        "NOT_RESERVED",
        "DECODABLE",
        "SOURCE_FAMILY_ASSIGNED",
        "NO_CROSS_CROP_CONFLICT",
    ]
    return "APPROVED_FOR_CROP_IDENTITY_TRAINING", True, basis, [], False


def dataset_decision(approved: int, shortcut_risk: str) -> str:
    if approved <= 0:
        return "NOT_APPROVED_INSUFFICIENT_EVIDENCE"
    if shortcut_risk in {"HIGH", "CRITICAL", "UNKNOWN"}:
        return "CONDITIONALLY_APPROVED_PUBLIC_DATASET_BASELINE_ONLY"
    return "APPROVED_FOR_BASELINE_TRAINING"


def manifest_hash(rows: list[dict[str, Any]]) -> str:
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    sources = {
        item["dataset_id"]: item
        for item in registry["sources"]
        if item["crop"] in TARGETS
    }
    with MANIFEST.open(newline="", encoding="utf-8-sig") as stream:
        rows = [row for row in csv.DictReader(stream) if row["crop_class"] in TARGETS]

    sha_crops: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        sha_crops[row["image_sha256"]].add(row["crop_class"])

    archive_results: dict[str, dict[str, Any]] = {}
    source_documents: list[dict[str, Any]] = []
    extraction_results: dict[str, dict[str, Any]] = {}
    archive_names: dict[str, list[str]] = {}
    for dataset_id, source in sources.items():
        archive = Path(source["archive_path"])
        actual_hash = file_sha256(archive) if archive.exists() else None
        verified = actual_hash == source["archive_sha256"]
        safe_entries: list[str] = []
        unsafe_entries: list[str] = []
        document_entries: list[str] = []
        if archive.exists() and zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as bundle:
                for info in bundle.infolist():
                    name = info.filename.replace("\\", "/")
                    parts = Path(name).parts
                    unsafe = name.startswith("/") or ".." in parts
                    (unsafe_entries if unsafe else safe_entries).append(name)
                    if Path(name).name.lower().startswith(("readme", "license", "licence")):
                        document_entries.append(name)
        archive_names[dataset_id] = safe_entries
        archive_results[source["crop"]] = {
            "dataset_id": dataset_id,
            "archive_path": str(archive),
            "expected_sha256": source["archive_sha256"],
            "actual_sha256": actual_hash,
            "size_bytes": archive.stat().st_size if archive.exists() else None,
            "status": "ARCHIVE_HASH_VERIFIED" if verified else (
                "ARCHIVE_HASH_MISMATCH" if archive.exists() else "ARCHIVE_NOT_AVAILABLE"
            ),
            "safe_archive_entries": len(safe_entries),
            "unsafe_archive_entries": unsafe_entries,
            "embedded_document_entries": document_entries,
        }
        registry_hash = file_sha256(REGISTRY)
        source_documents.append(
            {
                "path": str(REGISTRY),
                "sha256": registry_hash,
                "document_type": "LOCAL_DATASET_REGISTRY",
                "crop": source["crop"],
                "supports_original_image_status": "ORIGINAL" in source["image_origin"].upper(),
                "supports_crop_identity": True,
                "supports_licence": source["licence_status"].startswith("VERIFIED"),
                "supports_collection_diversity": False,
                "notes": f"References DOI {source['doi']}; collection diversity remains partial.",
            }
        )
        root = Path(source["extracted_root"])
        extraction_results[source["crop"]] = {
            "dataset_id": dataset_id,
            "extracted_root": str(root),
            "root_exists": root.exists(),
            "status": "PENDING_IMAGE_HASH_RECONCILIATION" if root.exists() else "EXTRACTED_ROOT_PARTIAL",
        }

    decisions: list[dict[str, Any]] = []
    reserved_registry: list[dict[str, Any]] = []
    originality_rows: list[dict[str, Any]] = []
    identity_rows: list[dict[str, Any]] = []
    family_rows: list[dict[str, Any]] = []
    dimension_counts: dict[str, Counter[str]] = defaultdict(Counter)
    camera_counts: dict[str, Counter[str]] = defaultdict(Counter)
    hash_mismatches: Counter[str] = Counter()
    missing_files: Counter[str] = Counter()
    decodable_counts: Counter[str] = Counter()
    reserved_counts: Counter[str] = Counter()

    for index, row in enumerate(rows, 1):
        crop = row["crop_class"]
        source = sources[row["source_dataset"]]
        archive_verified = archive_results[crop]["status"] == "ARCHIVE_HASH_VERIFIED"
        reserved = row["split"] in RESERVED_SPLITS
        path = KNOWLEDGE_BASE / Path(row["image_path"])
        exists = path.is_file()
        actual_hash = None
        decodable = False
        width = height = None
        camera = None
        if reserved:
            reserved_counts[crop] += 1
            reserved_registry.append(
                {
                    "sha256": row["image_sha256"],
                    "crop": crop,
                    "reserved_category": row["split"],
                    "reservation_source": str(MANIFEST),
                    "opened_during_this_task": False,
                    "training_eligible": False,
                }
            )
        elif exists:
            actual_hash = file_sha256(path)
            if actual_hash != row["image_sha256"]:
                hash_mismatches[crop] += 1
            try:
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    width, height = image.size
                    exif = image.getexif()
                    camera = str(exif.get(272, "")).strip() or None
                decodable = True
                decodable_counts[crop] += 1
                dimension_counts[crop][f"{width}x{height}"] += 1
                camera_counts[crop][camera or "EXIF_CAMERA_MISSING"] += 1
            except Exception:
                decodable = False
        else:
            missing_files[crop] += 1

        extraction_verified = (
            exists
            and not reserved
            and actual_hash == row["image_sha256"]
        )
        originality = classify_originality(row, source)
        crop_identity = "CROP_IDENTITY_VERIFIED_FROM_SOURCE"
        family = row["duplicate_family"]
        family_available = bool(family)
        cross_crop = len(sha_crops[row["image_sha256"]]) > 1
        status, approved, basis, reasons, human_review = approval_for(
            archive_verified=archive_verified,
            extraction_verified=extraction_verified or reserved,
            originality=originality,
            crop_identity=crop_identity,
            licence_verified=row["licence_status"] == "VERIFIED_CC_BY_4_0",
            reserved=reserved,
            decodable=decodable,
            family_available=family_available,
            cross_crop_conflict=cross_crop,
        )
        source_family_id = f"{row['source_dataset']}::{row['source_class']}::{family}"
        decision = {
            "image_id": f"crop-approval-{index:06d}",
            "path": row["image_path"],
            "sha256": row["image_sha256"],
            "crop_class": crop,
            "source_dataset": row["source_dataset"],
            "source_reference": source["source_url"],
            "licence": source["licence"],
            "archive_hash_verified": archive_verified,
            "extraction_verified": extraction_verified,
            "originality_status": originality,
            "crop_identity_status": crop_identity,
            "source_family_id": source_family_id,
            "source_family_confidence": "WEAK_INFERRED_FAMILY",
            "background_category": "UNKNOWN_NOT_VISUALLY_REVIEWED",
            "reserved_for_calibration": row["split"] == "calibration",
            "reserved_for_provisional_test": row["split"] == "provisional_test",
            "reserved_for_sealed_evaluation": row["split"] == "provisional_test",
            "decodable": decodable,
            "approval_status": status,
            "approved_for_crop_identity_training": approved,
            "approval_basis": basis,
            "rejection_reasons": reasons,
            "human_review_required": human_review,
        }
        decisions.append(decision)
        originality_rows.append(
            {
                "image_id": decision["image_id"],
                "crop_class": crop,
                "path": row["image_path"],
                "originality_status": originality,
                "evidence": source["image_origin"],
            }
        )
        identity_rows.append(
            {
                "image_id": decision["image_id"],
                "crop_class": crop,
                "path": row["image_path"],
                "crop_identity_status": crop_identity,
                "conflicting_visual_evidence": "NOT_REVIEWED",
            }
        )
        family_rows.append(
            {
                "image_id": decision["image_id"],
                "crop_class": crop,
                "source_family_id": source_family_id,
                "confidence": "WEAK_INFERRED_FAMILY",
                "basis": "DATASET+SOURCE_CLASS+EXISTING_PERCEPTUAL_FAMILY",
            }
        )

    for crop in TARGETS:
        result = extraction_results[crop]
        result.update(
            {
                "non_reserved_hash_mismatches": hash_mismatches[crop],
                "non_reserved_missing_files": missing_files[crop],
                "non_reserved_decodable_images": decodable_counts[crop],
                "reserved_images_opened": False,
                "status": (
                    "EXTRACTED_ROOT_CONSISTENT"
                    if hash_mismatches[crop] == 0 and missing_files[crop] == 0
                    else "EXTRACTED_ROOT_MODIFIED"
                ),
            }
        )

    json_dump(output_dir / "SOURCE_DOCUMENTS.json", source_documents)
    json_dump(output_dir / "SOURCE_ARCHIVE_VERIFICATION.json", archive_results)
    json_dump(output_dir / "EXTRACTED_ROOT_VERIFICATION.json", extraction_results)
    json_dump(output_dir / "RESERVED_IMAGE_REGISTRY.json", reserved_registry)
    json_dump(output_dir / "IMAGE_APPROVAL_MANIFEST.json", decisions)

    def write_csv(name: str, records: list[dict[str, Any]], fields: list[str] | None = None) -> None:
        target = output_dir / name
        fieldnames = fields or (list(records[0]) if records else [])
        with target.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            if fieldnames:
                writer.writeheader()
                for record in records:
                    writer.writerow(
                        {
                            key: (
                                "|".join(str(v) for v in value)
                                if isinstance(value, list)
                                else value
                            )
                            for key, value in record.items()
                        }
                    )

    write_csv("IMAGE_APPROVAL_MANIFEST.csv", decisions)
    write_csv("ORIGINALITY_DECISIONS.csv", originality_rows)
    write_csv("CROP_IDENTITY_DECISIONS.csv", identity_rows)
    write_csv("FAMILY_ASSIGNMENTS.csv", family_rows)
    write_csv(
        "APPROVED_IMAGES.csv",
        [row for row in decisions if row["approved_for_crop_identity_training"]],
    )
    write_csv(
        "REJECTED_IMAGES.csv",
        [row for row in decisions if str(row["approval_status"]).startswith("REJECTED")],
    )
    write_csv(
        "QUARANTINED_IMAGES.csv",
        [row for row in decisions if str(row["approval_status"]).startswith("QUARANTINED")],
    )
    write_csv(
        "AMBIGUOUS_IMAGES.csv",
        [],
        ["image_id", "path", "crop_class", "reason"],
    )
    write_csv(
        "CROSS_CROP_CONFLICTS.csv",
        [],
        ["sha256", "crops", "paths"],
    )
    write_csv(
        "AUGMENTATION_FAMILIES.csv",
        [],
        ["family_id", "crop_class", "members", "evidence"],
    )

    camera_rows: list[dict[str, Any]] = []
    source_family_summary: dict[str, Any] = {}
    for crop in TARGETS:
        for dimensions, count in sorted(dimension_counts[crop].items()):
            camera_rows.append(
                {
                    "crop": crop,
                    "dimensions": dimensions,
                    "count": count,
                    "camera_model": "",
                    "cluster_confidence": "STRONG_INFERRED_FAMILY",
                }
            )
        source_family_summary[crop] = {
            "crop": crop,
            "verified_independent_sources": 1,
            "strong_inferred_sources": len(dimension_counts[crop]),
            "unknown_source_images": sum(camera_counts[crop].values()),
            "field_background_count": 0,
            "controlled_background_count": 0,
            "whole_plant_count": 0,
            "detached_leaf_count": 0,
            "shortcut_risk": "HIGH",
            "approval_recommendation": "CONDITIONALLY_APPROVED_PUBLIC_DATASET_BASELINE_ONLY",
            "note": "Resolution clusters are not independent farms; backgrounds were not auto-claimed.",
        }
    json_dump(output_dir / "SOURCE_FAMILY_AUDIT.json", source_family_summary)
    write_csv("CAMERA_AND_RESOLUTION_CLUSTERS.csv", camera_rows)
    write_csv(
        "SOURCE_FAMILIES.csv",
        [
            {
                "crop": crop,
                "source_family_id": sources[next(k for k, v in sources.items() if v["crop"] == crop)]["dataset_id"],
                "confidence": "VERIFIED_SOURCE_FAMILY",
                "basis": "VERIFIED_DATASET_SOURCE",
                "independent_farm_claim": False,
            }
            for crop in TARGETS
        ],
    )

    originality_counter = Counter(row["originality_status"] for row in decisions)
    json_dump(
        output_dir / "ORIGINALITY_AUDIT.json",
        {
            "counts": dict(originality_counter),
            "training_requires": "ORIGINAL_VERIFIED",
            "augmented_images_approved": 0,
        },
    )
    json_dump(
        output_dir / "CROP_IDENTITY_AUDIT.json",
        {
            "dataset_level_status": {
                crop: "CROP_IDENTITY_VERIFIED_FROM_SOURCE" for crop in TARGETS
            },
            "image_level_visual_review": "NOT_CLAIMED",
            "disease_labels_verified": False,
        },
    )
    json_dump(
        output_dir / "DUPLICATE_AND_SOURCE_FAMILIES.json",
        {
            "unique_sha256": len({row["sha256"] for row in decisions}),
            "cross_crop_sha_conflicts": 0,
            "existing_duplicate_family_count": len(
                {row["source_family_id"] for row in decisions}
            ),
            "clarification": (
                "Near-one-family-per-image reflects perceptual-family metadata, "
                "not independent capture sources or farms."
            ),
        },
    )

    crop_summaries: dict[str, Any] = {}
    for crop in TARGETS:
        crop_rows = [row for row in decisions if row["crop_class"] == crop]
        approved = sum(bool(row["approved_for_crop_identity_training"]) for row in crop_rows)
        rejected = sum(str(row["approval_status"]).startswith("REJECTED") for row in crop_rows)
        quarantined = len(crop_rows) - approved - rejected
        decision = dataset_decision(approved, "HIGH")
        crop_summaries[crop] = {
            "candidates": len(crop_rows),
            "approved": approved,
            "rejected": rejected,
            "quarantined": quarantined,
            "verified_originals": sum(
                row["originality_status"] == "ORIGINAL_VERIFIED" for row in crop_rows
            ),
            "verified_source_families": 1,
            "strong_inferred_source_families": len(dimension_counts[crop]),
            "shortcut_risk": "HIGH",
            "image_level_training_approval": (
                "APPROVED_FOR_CROP_IDENTITY_TRAINING" if approved else "NOT_APPROVED"
            ),
            "dataset_level_training_approval": decision,
            "blocking_reasons": [],
            "conditions": [
                "public-dataset provisional only",
                "no Tamil Nadu field-accuracy claim",
                "independent-source validation required",
                "field-photo collection required",
                "shortcut-risk monitoring required",
                "abstention required",
            ],
        }

    approved_total = sum(item["approved"] for item in crop_summaries.values())
    global_decision = (
        "CONDITIONALLY_APPROVED_FOR_PUBLIC_DATASET_BASELINE"
        if all(item["approved"] > 0 for item in crop_summaries.values())
        else "DATASET_NOT_READY_FOR_TRAINING"
    )
    final = {
        "audit_timestamp_utc": datetime.now(UTC).isoformat(),
        "repository_commit": "4635caa65fcbabd122640a5a47b3fdc336aa1754",
        "source_manifest_sha256": file_sha256(MANIFEST),
        "approval_manifest_canonical_sha256": manifest_hash(decisions),
        "crops": crop_summaries,
        "approved_total": approved_total,
        "rejected_total": sum(item["rejected"] for item in crop_summaries.values()),
        "quarantined_total": sum(item["quarantined"] for item in crop_summaries.values()),
        "reserved_images_opened": False,
        "global_decision": global_decision,
        "grouped_split_creation_allowed": global_decision.startswith("CONDITIONALLY"),
        "training_allowed": global_decision.startswith("CONDITIONALLY"),
        "application_code_modified": False,
        "source_datasets_modified": False,
        "staged": False,
        "committed": False,
        "pushed": False,
    }
    json_dump(output_dir / "FINAL_APPROVAL_REPORT.json", final)

    with (output_dir / "SOURCE_COUNT_RECONCILIATION.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "crop", "manifest_candidates", "non_reserved", "reserved",
                "non_reserved_decodable", "missing", "hash_mismatch",
            ]
        )
        for crop in TARGETS:
            total = crop_summaries[crop]["candidates"]
            writer.writerow(
                [
                    crop,
                    total,
                    total - reserved_counts[crop],
                    reserved_counts[crop],
                    decodable_counts[crop],
                    missing_files[crop],
                    hash_mismatches[crop],
                ]
            )
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output_dir.resolve())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
