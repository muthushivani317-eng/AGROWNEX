"""Inventory every local agricultural PDF and extract six-crop evidence candidates."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path(r"D:\AgrowAI\Reference_books_pdf")
STAMP = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
AUDIT = ROOT / "docs/model_audits/six_crop_recommendation_knowledge_and_integration" / STAMP
CROPS = {
    "banana": ("banana",),
    "paddy": ("paddy", "rice"),
    "cotton": ("cotton",),
    "groundnut": ("groundnut", "peanut"),
    "redgram": ("redgram", "pigeonpea", "pigeon pea"),
    "chilli": ("chilli", "chillies", "capsicum"),
}
MANAGEMENT = (
    "management", "control", "treatment", "prevention", "spray", "fungicide",
    "bactericide", "biological", "sanitation", "dose", "symptom",
)
AUTHORITY_MARKERS = {
    "OFFICIAL_UNIVERSITY_SOURCE": ("tamil nadu agricultural university", "tnau"),
    "OFFICIAL_RESEARCH_INSTITUTE_SOURCE": (
        "indian council of agricultural research", "icar", "central institute",
    ),
    "OFFICIAL_GOVERNMENT_SOURCE": (
        "government of india", "government of tamil nadu", "department of agriculture",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def authority(text: str) -> str:
    for status, markers in AUTHORITY_MARKERS.items():
        if any(marker in text for marker in markers):
            return status
    return "UNKNOWN_AUTHORITY"


def write_json(name: str, value: object) -> None:
    (AUDIT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)
    inventory: list[dict] = []
    extracted: list[dict] = []
    failures: list[dict] = []
    seen_hashes: dict[str, str] = {}
    for path in sorted(REFERENCE.rglob("*.pdf")):
        digest = sha256(path)
        duplicate_of = seen_hashes.get(digest)
        seen_hashes.setdefault(digest, str(path))
        record = {
            "file_name": path.name, "full_path": str(path), "file_size": path.stat().st_size,
            "sha256": digest, "page_count": 0, "pdf_readability": "UNREADABLE",
            "text_extraction_status": "FAILED", "image_only_scanned_status": "UNKNOWN",
            "ocr_requirement": "UNKNOWN", "language": "UNKNOWN", "publisher": None,
            "title": None, "edition": None, "publication_year": None,
            "apparent_official_status": "UNKNOWN_AUTHORITY", "crops_covered": [],
            "disease_management_relevance": False, "chemical_recommendation_presence": False,
            "tables_present": False, "annexures_present": False,
            "duplicate_book_status": "DUPLICATE_SOURCE" if duplicate_of else "UNIQUE_HASH",
            "duplicate_of": duplicate_of, "superseded_version_suspicion": "NOT_DETERMINED",
            "extraction_limitations": [], "review_priority": "LOW",
        }
        try:
            reader = PdfReader(path, strict=False)
            record["page_count"] = len(reader.pages)
            metadata = reader.metadata or {}
            record["title"] = metadata.get("/Title") or None
            record["publisher"] = metadata.get("/Author") or None
            all_text_chars = 0
            first_text = []
            for index, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                except Exception as exc:  # noqa: BLE001
                    failures.append({
                        "source_file": str(path), "source_pdf_sha256": digest,
                        "pdf_page_index": index, "status": "SOURCE_PAGE_UNREADABLE",
                        "error_category": type(exc).__name__,
                    })
                    continue
                all_text_chars += len(text)
                if index < 5:
                    first_text.append(text)
                lowered = text.lower()
                matched_crops = [
                    crop for crop, terms in CROPS.items() if any(term in lowered for term in terms)
                ]
                if matched_crops and any(term in lowered for term in MANAGEMENT):
                    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
                    relevant = [
                        line for line in lines
                        if any(term in line.lower() for terms in CROPS.values() for term in terms)
                        or any(term in line.lower() for term in MANAGEMENT)
                    ][:12]
                    extracted.append({
                        "source_pdf_sha256": digest, "source_file": path.name,
                        "pdf_page_index": index, "printed_page": None,
                        "section_title": relevant[0] if relevant else None,
                        "crop_context": matched_crops, "disease_heading": None,
                        "table_or_paragraph_identifier": f"pdf-page-{index}",
                        "extraction_method": "NATIVE_PDF_TEXT",
                        "extraction_confidence": "CANDIDATE_REQUIRES_INTERNAL_REVIEW",
                        "raw_source_excerpt": "\n".join(relevant)[:3000],
                        "normalized_structured_value": None,
                        "reviewer_status": "INTERNAL_REVIEW_REQUIRED",
                    })
            cover = "\n".join(first_text).lower()
            crops = [crop for crop, terms in CROPS.items() if any(term in cover for term in terms)]
            record["crops_covered"] = crops
            record["pdf_readability"] = "READABLE"
            record["text_extraction_status"] = "NATIVE_TEXT_EXTRACTED" if all_text_chars else "NO_TEXT"
            record["image_only_scanned_status"] = "LIKELY_SCANNED" if all_text_chars < 100 else "TEXT_BEARING"
            record["ocr_requirement"] = "REQUIRED" if all_text_chars < 100 else "NOT_REQUIRED"
            record["language"] = "TAMIL_OR_MIXED" if re.search(r"[\u0B80-\u0BFF]", cover) else "ENGLISH_OR_OTHER"
            record["apparent_official_status"] = authority(cover)
            record["disease_management_relevance"] = bool(crops and any(x in cover for x in MANAGEMENT))
            record["chemical_recommendation_presence"] = any(x in cover for x in ("fungicide", "pesticide", "insecticide"))
            record["tables_present"] = "table" in cover
            record["annexures_present"] = "annexure" in cover or "appendix" in cover
            record["review_priority"] = "HIGH" if record["disease_management_relevance"] else "LOW"
        except Exception as exc:  # noqa: BLE001
            record["extraction_limitations"].append(type(exc).__name__)
            failures.append({
                "source_file": str(path), "source_pdf_sha256": digest,
                "status": "UNREADABLE", "error_category": type(exc).__name__,
            })
        inventory.append(record)

    fields = list(inventory[0])
    with (AUDIT / "PDF_SOURCE_INVENTORY.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in inventory:
            writer.writerow({key: json.dumps(value) if isinstance(value, list) else value for key, value in row.items()})
    write_json("PDF_SOURCE_INVENTORY.json", inventory)
    write_json("SOURCE_AUTHORITY_CLASSIFICATION.json", {
        "counts": Counter(row["apparent_official_status"] for row in inventory),
        "rule": "Authority is assigned only from text visible inside the PDF; otherwise UNKNOWN_AUTHORITY.",
    })
    write_json("SOURCE_EXTRACTION_REPORT.json", {
        "candidate_count": len(extracted), "items": extracted,
        "activation_status": "INTERNAL_REVIEW_REQUIRED",
        "note": "Candidates preserve page and crop context but are not active recommendations.",
    })
    write_json("SOURCE_EXTRACTION_FAILURES.json", failures)

    labels = {
        "banana": {
            "model_name": "banana_v3", "runtime_available": True,
            "labels": [
                "banana__healthy", "banana__cordana_leaf_spot",
                "banana__pestalotiopsis_leaf_spot", "banana__sigatoka_leaf_spot",
            ],
        },
        "paddy": {"model_name": "mobilenetv3_small_v1", "runtime_available": True, "labels": ["paddy_healthy", "rice_blast", "rice_brown_leaf_spot", "rice_tungro"]},
        "cotton": {"model_name": "mobilenetv3_small_v1", "runtime_available": True, "labels": ["cotton_fusarium_wilt", "cotton_healthy", "cotton_verticillium_wilt"]},
        "groundnut": {"model_name": "mobilenetv3_small_v1", "runtime_available": True, "labels": ["groundnut_healthy", "groundnut_rust"]},
        "redgram": {"model_name": "redgram_v3", "runtime_available": False, "labels": [], "status": "MODEL_LABEL_PENDING_FINAL_RUNTIME"},
        "chilli": {"model_name": "chilli_v2", "runtime_available": False, "labels": [], "status": "MODEL_LABEL_PENDING_FINAL_RUNTIME"},
    }
    write_json("MODEL_LABEL_REGISTRY.json", labels)
    mappings = [
        {"crop": crop, "model_label": label, "mapping_status": "MANUAL_REVIEW_REQUIRED", "active": False}
        for crop, data in labels.items() for label in data["labels"]
    ]
    write_json("DISEASE_NAME_MAPPING.json", mappings)
    write_json("DISEASE_MAPPING_CONFLICTS.json", [])

    statuses = {}
    for crop in CROPS:
        status = "MODEL_LABEL_PENDING_FINAL_RUNTIME" if crop in {"redgram", "chilli"} else "INSUFFICIENT_SOURCE_EVIDENCE"
        statuses[crop] = status
        write_json(f"{crop.upper()}_RECOMMENDATION_REPORT.json", {
            "crop": crop, "status": status, "runtime_labels": labels[crop]["labels"],
            "active_recommendations": 0, "verification_label": "VERIFY AGAINST OFFICIAL SOURCE",
        })
    write_json("SIX_CROP_RECOMMENDATION_COVERAGE.json", statuses)
    empty_reports = {
        "SYMPTOM_MAPPING_REPORT.json": "SOURCE_CANDIDATES_REQUIRE_REVIEW",
        "IMMEDIATE_ACTION_REPORT.json": "SOURCE_CANDIDATES_REQUIRE_REVIEW",
        "PREVENTION_REPORT.json": "SOURCE_CANDIDATES_REQUIRE_REVIEW",
        "CULTURAL_PRACTICES_REPORT.json": "SOURCE_CANDIDATES_REQUIRE_REVIEW",
        "BIOLOGICAL_OPTIONS_REPORT.json": "SOURCE_CANDIDATES_REQUIRE_REVIEW",
        "CHEMICAL_OPTIONS_REPORT.json": "BLOCKED_REGULATORY_UNVERIFIED",
        "BRAND_FILTER_REPORT.json": "IMPLEMENTED_IN_SCHEMA_VALIDATION",
        "SOURCE_CONFLICT_REPORT.json": "NO_ACTIVE_RECOMMENDATIONS_TO_COMPARE",
        "TAMIL_TRANSLATION_REPORT.json": "TAMIL_TRANSLATION_REVIEW_REQUIRED",
        "ENGLISH_RENDERING_REPORT.json": "STRUCTURE_IMPLEMENTED",
        "RECOMMENDATION_SCHEMA_REPORT.json": "IMPLEMENTED_FAIL_CLOSED",
        "BACKEND_INTEGRATION_REPORT.json": "SERVICE_IMPLEMENTED_PIPELINE_ACTIVATION_BLOCKED",
        "MOBILE_INTEGRATION_REPORT.json": "REUSABLE_COMPONENT_IMPLEMENTED",
        "RECOMMENDATION_INTEGRITY_REPORT.json": "ACTIVE_BUNDLE_NOT_CREATED",
    }
    for name, status in empty_reports.items():
        write_json(name, {"status": status, "active_recommendations": 0})
    write_json("PIPELINE_SUPPRESSION_RULES.json", {
        "blocked": ["crop_mismatch", "crop_id_abstention", "disease_abstention", "low_confidence", "healthy", "unknown_disease", "integrity_failure", "no_reviewed_source"],
    })
    write_json("BETA_READINESS_MATRIX.json", statuses)
    write_json("BLOCKERS.json", {
        "primary": "Source candidates and Tamil translations require internal human review.",
        "runtime_label_pending": ["redgram", "chilli"],
        "active_recommendation_count": 0,
    })
    summary = {
        "status": "SIX_CROP_RECOMMENDATION_FOUNDATION_READY_RUNTIME_LABELS_PENDING",
        "total_pdfs": len(inventory),
        "readable": sum(row["pdf_readability"] == "READABLE" for row in inventory),
        "unreadable": sum(row["pdf_readability"] != "READABLE" for row in inventory),
        "candidate_extractions": len(extracted),
        "active_recommendations": 0,
        "official_accuracy_claim": False,
        "field_validated": False,
        "expert_verified": False,
    }
    write_json("FINAL_REPORT.json", summary)
    (AUDIT / "FINAL_REPORT.md").write_text(
        "# Six-crop recommendation knowledge audit\n\n"
        f"- Status: `{summary['status']}`\n"
        f"- PDFs inventoried: {len(inventory)}; readable: {summary['readable']}; unreadable: {summary['unreadable']}.\n"
        f"- Page-context extraction candidates: {len(extracted)}; all remain inactive pending review.\n"
        "- No recommendation, chemical option, Tamil translation, or official/field claim was invented.\n"
        "- Redgram V3 and Chilli V2 final runtime labels remain pending.\n",
        encoding="utf-8",
    )
    for name in ("API_TEST_RESULTS.json", "MOBILE_TEST_RESULTS.json", "FULL_TEST_RESULTS.json"):
        write_json(name, {"status": "PENDING_TEST_EXECUTION"})
    (AUDIT / "NEXT_ACTIONS.md").write_text(
        "# Next actions\n\nPerform page-by-page internal review of extracted candidates and approve exact disease mappings and Tamil translations before creating any active recommendation bundle.\n",
        encoding="utf-8",
    )
    (AUDIT / "CHANGED_FILES.txt").write_text("Generated after validation.\n", encoding="utf-8")
    (AUDIT / "COMMANDS_EXECUTED.txt").write_text("Generated after validation.\n", encoding="utf-8")
    print(AUDIT)


if __name__ == "__main__":
    sys.exit(main())
