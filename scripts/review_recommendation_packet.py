"""Validate and record an explicit human recommendation review decision."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "recommendation_knowledge"
OFFICIAL = {
    "OFFICIAL_GOVERNMENT",
    "OFFICIAL_UNIVERSITY",
    "OFFICIAL_RESEARCH_INSTITUTE",
}


def validate_approval(document: dict) -> list[str]:
    errors: list[str] = []
    required = (
        "crop_id", "runtime_label_exact", "runtime_class_index",
        "canonical_disease_id", "canonical_disease_name_en",
        "mapping_review_status", "recommendation_review_status",
        "reviewer_name", "reviewed_at_utc",
    )
    for field in required:
        if document.get(field) in (None, ""):
            errors.append(f"missing:{field}")
    if document.get("mapping_review_status") != "HUMAN_APPROVED":
        errors.append("mapping_not_human_approved")
    if document.get("recommendation_review_status") != "HUMAN_APPROVED":
        errors.append("recommendation_not_human_approved")
    if document.get("tamil_review_status") != "HUMAN_APPROVED":
        errors.append("tamil_not_human_approved")
    for category in (
        "symptoms", "immediate_actions", "prevention", "cultural_practices",
        "biological_options", "chemical_options", "avoid_actions",
    ):
        for index, item in enumerate(document.get(category, [])):
            prefix = f"{category}[{index}]"
            if item.get("human_approved") is not True:
                errors.append(f"{prefix}:not_human_approved")
            if not item.get("source_id") or not item.get("page_number"):
                errors.append(f"{prefix}:missing_citation")
            if not item.get("exact_excerpt"):
                errors.append(f"{prefix}:missing_exact_excerpt")
            if item.get("source_authority") not in OFFICIAL:
                errors.append(f"{prefix}:authority_not_eligible")
            if category != "chemical_options" and (
                not item.get("text_en") or not item.get("text_ta")
            ):
                errors.append(f"{prefix}:bilingual_text_incomplete")
            if category == "chemical_options":
                for field in ("active_ingredient_en", "dosage", "application_method_en"):
                    if not item.get(field):
                        errors.append(f"{prefix}:missing_{field}")
                if item.get("brand_name"):
                    errors.append(f"{prefix}:brand_forbidden")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("decision_file", type=Path)
    parser.add_argument("--action", choices=("validate", "approve", "reject"), default="validate")
    args = parser.parse_args()
    document = json.loads(args.decision_file.read_text(encoding="utf-8"))
    errors = validate_approval(document)
    if args.action == "validate":
        print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
        return int(bool(errors))
    if args.action == "approve":
        if errors:
            print(json.dumps({"approved": False, "errors": errors}, indent=2))
            return 1
        destination = KNOWLEDGE / "approved" / args.decision_file.name
    else:
        if not document.get("reviewer_name"):
            print('{"rejected":false,"errors":["missing:reviewer_name"]}')
            return 1
        destination = KNOWLEDGE / "rejected" / args.decision_file.name
    document["decision_recorded_at_utc"] = datetime.now(UTC).isoformat()
    destination.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(args.decision_file, KNOWLEDGE / "pending" / args.decision_file.name)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
