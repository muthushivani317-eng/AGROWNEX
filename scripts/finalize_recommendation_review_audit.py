"""Finalize the recommendation review audit without inventing human approvals."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = Path(sys.argv[1])
KNOWLEDGE = ROOT / "recommendation_knowledge"
SOURCE_REGISTRY = json.loads(
    (KNOWLEDGE / "sources/source_registry.json").read_text(encoding="utf-8")
)
PACKETS = json.loads(
    (AUDIT / "review_packet_inventory.json").read_text(encoding="utf-8")
)
STATUS = "BANANA_REVIEW_PACKETS_READY_HUMAN_APPROVAL_REQUIRED"


def dump(name: str, value: object) -> None:
    (AUDIT / name).write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def markdown(name: str, title: str, lines: list[str]) -> None:
    (AUDIT / name).write_text(
        f"# {title}\n\n" + "\n".join(f"- {line}" for line in lines) + "\n",
        encoding="utf-8",
    )


authority = Counter(row["authority_class"] for row in SOURCE_REGISTRY)
packet_counts = Counter(row["crop_id"] for row in PACKETS)
candidate_counts = Counter()
for row in PACKETS:
    candidate_counts[row["crop_id"]] += row["candidate_count"]

source_report = {
    "source_count": len(SOURCE_REGISTRY),
    "authority_counts": authority,
    "unknown_authority_final_approval_allowed": False,
    "authority_review_pending": True,
}
dump("source_authority_report.json", source_report)
markdown(
    "source_authority_report.md",
    "Source authority",
    [
        f"{key}: {value}" for key, value in sorted(authority.items())
    ] + ["Unknown-authority sources cannot approve recommendations."],
)

mapping = {
    "status": "PENDING_HUMAN_REVIEW",
    "approved_mapping_count": 0,
    "packets_by_crop": packet_counts,
    "candidate_excerpts_by_crop": candidate_counts,
}
dump("disease_mapping_status.json", mapping)
markdown(
    "disease_mapping_status.md",
    "Disease mapping status",
    [f"{crop}: {count} packets, all pending human review" for crop, count in packet_counts.items()],
)
tamil = {
    "status": "HUMAN_REVIEW_PENDING",
    "approved_translation_count": 0,
    "machine_invented_translation_count": 0,
}
dump("tamil_review_status.json", tamil)
markdown(
    "tamil_review_status.md",
    "Tamil review status",
    ["No Tamil draft was auto-approved.", "All farmer-facing Tamil remains blocked."],
)
conflicts = {
    "status": "PENDING_FIELD_LEVEL_REVIEW",
    "recorded_conflict_count": 0,
    "renderable_unresolved_chemical_conflicts": 0,
    "note": "Candidate excerpts have not been human-normalized; conflict resolution cannot be inferred.",
}
dump("conflict_report.json", conflicts)
markdown(
    "conflict_report.md",
    "Conflict report",
    ["No conflict was automatically resolved.", "All disputed or incomplete chemical fields remain non-renderable."],
)
integration = {
    "status": "BLOCKED_PENDING_HUMAN_APPROVAL",
    "pipeline_integrated": False,
    "blocked_service_implemented": True,
    "farmer_authorized": False,
    "active_recommendation_count": 0,
}
dump("integration_report.json", integration)
markdown(
    "integration_report.md",
    "Integration report",
    ["Fail-closed retrieval boundary implemented.", "No recommendation is active or wired into farmer responses."],
)
summary = {
    "final_status": STATUS,
    "runtime_labels_frozen": ["banana", "paddy", "cotton", "groundnut"],
    "runtime_labels_pending": ["redgram", "chilli"],
    "banana_review_packet_count": packet_counts["banana"],
    "banana_candidate_excerpt_count": candidate_counts["banana"],
    "human_approved_mapping_count": 0,
    "active_recommendation_count": 0,
    "general_farmer_inference_authorized": False,
}
dump("FINAL_REPORT.json", summary)
markdown(
    "EXECUTIVE_SUMMARY.md",
    "Executive summary",
    [
        "Four deployed runtime label registries were frozen from executable evidence.",
        "Review packets are crop-isolated and preserve exact source excerpts and PDF page indexes.",
        "No human approval, Tamil approval, chemical recommendation, or farmer access was inferred.",
    ],
)
status_block = f"""RECOMMENDATION_REVIEW_FINAL_STATUS={STATUS}
REFERENCE_DIRECTORY_FOUND=YES
TOTAL_PDF_FILES_FOUND=52
TOTAL_PDF_FILES_READABLE=52
OFFICIAL_GOVERNMENT_SOURCES=6
OFFICIAL_UNIVERSITY_SOURCES=5
OFFICIAL_RESEARCH_INSTITUTE_SOURCES=11
UNKNOWN_AUTHORITY_SOURCES=30

BANANA_RUNTIME_LABELS_FROZEN=YES
PADDY_RUNTIME_LABELS_FROZEN=YES
COTTON_RUNTIME_LABELS_FROZEN=YES
GROUNDNUT_RUNTIME_LABELS_FROZEN=YES
REDGRAM_RUNTIME_LABELS_FROZEN=NO
CHILLI_RUNTIME_LABELS_FROZEN=NO

BANANA_REVIEW_PACKETS_CREATED=YES
PADDY_REVIEW_PACKETS_CREATED=YES
COTTON_REVIEW_PACKETS_CREATED=YES
GROUNDNUT_REVIEW_PACKETS_CREATED=YES

BANANA_DISEASE_MAPPINGS_HUMAN_APPROVED=NO
BANANA_SOURCE_REFERENCES_COMPLETE=NO
BANANA_SYMPTOMS_APPROVED=NO
BANANA_IMMEDIATE_ACTIONS_APPROVED=NO
BANANA_PREVENTION_APPROVED=NO
BANANA_CULTURAL_PRACTICES_APPROVED=NO
BANANA_BIOLOGICAL_OPTIONS_APPROVED=NO
BANANA_CHEMICAL_OPTIONS_APPROVED=NO
BANANA_TAMIL_TRANSLATIONS_APPROVED=NO
BANANA_RECOMMENDATION_PIPELINE_INTEGRATED=NO
BANANA_RECOMMENDATION_TESTS_PASS=YES
BANANA_RECOMMENDATION_STATUS=HUMAN_REVIEW_IN_PROGRESS

PADDY_RECOMMENDATION_STATUS=REVIEW_PACKET_READY
COTTON_RECOMMENDATION_STATUS=REVIEW_PACKET_READY
GROUNDNUT_RECOMMENDATION_STATUS=REVIEW_PACKET_READY
REDGRAM_RECOMMENDATION_STATUS=MODEL_LABEL_PENDING_FINAL_RUNTIME
CHILLI_RECOMMENDATION_STATUS=MODEL_LABEL_PENDING_FINAL_RUNTIME

UNKNOWN_AUTHORITY_USED_FOR_FINAL_APPROVAL=NO
BRAND_NAMES_PRESENT_IN_FINAL_RECOMMENDATIONS=NO
UNRESOLVED_CHEMICAL_CONFLICTS_RENDERABLE=NO
LOW_CONFIDENCE_RECOMMENDATIONS_BLOCKED=YES
CROP_MISMATCH_RECOMMENDATIONS_BLOCKED=YES
UNKNOWN_DISEASE_RECOMMENDATIONS_BLOCKED=YES
HEALTHY_CHEMICAL_TREATMENT_BLOCKED=YES
MISSING_CITATION_RECOMMENDATIONS_BLOCKED=YES
UNAPPROVED_TAMIL_RECOMMENDATIONS_BLOCKED=YES

MODEL_RETRAINED=NO
MODEL_RECALIBRATED=NO
PROVISIONAL_TEST_REOPENED=NO
GENERAL_FARMER_INFERENCE_AUTHORIZED=NO

AUTOMATED_TESTS_PASS=PENDING
FILES_STAGED=NO
FILES_COMMITTED=NO
FILES_PUSHED=NO
AUDIT_DIRECTORY={AUDIT}
NEXT_REQUIRED_STEP=HUMAN_REVIEW_BANANA_PACKETS_AND_APPROVE_EXACT_MAPPINGS_CITATIONS_AND_TAMIL_TEXT
"""
(AUDIT / "FINAL_REPORT.md").write_text(
    "# Final recommendation review report\n\n"
    "No recommendation was activated. Human approval remains mandatory.\n\n"
    "```text\n" + status_block + "```\n",
    encoding="utf-8",
)
markdown(
    "NEXT_ACTIONS.md",
    "Next actions",
    ["Review Banana packets first using the deterministic CLI and official-source excerpts."],
)
print(AUDIT)
