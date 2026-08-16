"""Freeze runtime labels and build non-approving evidence review packets."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "recommendation_knowledge"
PREVIOUS_AUDIT = (
    ROOT / "docs/model_audits/six_crop_recommendation_knowledge_and_integration"
    / "20260730T103944Z"
)
STAMP = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
AUDIT = (
    ROOT / "docs/model_audits/six_crop_recommendation_review_and_integration" / STAMP
)
BANANA_MAPPING = ROOT / "backend/app/banana_v3/artifacts/runtime/class_mappings.json"
BANANA_MODEL = ROOT / "backend/app/banana_v3/artifacts/onnx/disease_classifier.onnx"
BANANA_LOADER = ROOT / "backend/app/banana_v3/config.py"
LEGACY_MAPPING = (
    ROOT / "backend/model_artifacts/legacy_joint_v1_crop_constrained/runtime"
    / "class_mapping.json"
)
LEGACY_MODEL = (
    ROOT / "backend/model_artifacts/legacy_joint_v1_crop_constrained/onnx"
    / "model_opset17.onnx"
)
LEGACY_LOADER = ROOT / "backend/app/modules/disease/ml_runtime/constants.py"
VERIFY = "VERIFY_AGAINST_OFFICIAL_SOURCE"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalized(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def registry(
    crop: str,
    labels: list[str],
    healthy: set[str],
    model: Path,
    loader: Path,
    label_source: Path,
) -> dict:
    return {
        "crop_id": crop,
        "model_artifact_path": str(model.relative_to(ROOT)),
        "model_artifact_sha256": sha(model),
        "runtime_loader_path": str(loader.relative_to(ROOT)),
        "runtime_label_source_path": str(label_source.relative_to(ROOT)),
        "runtime_label_source_sha256": sha(label_source),
        "label_count": len(labels),
        "labels": [
            {
                "class_index": index,
                "runtime_label_exact": label,
                "normalized_lookup_key": normalized(label),
                "is_healthy": label in healthy,
                "is_unknown_or_background": False,
            }
            for index, label in enumerate(labels)
        ],
        "registry_status": "FROZEN",
        "blocking_reason": None,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }


def field_type(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("symptom", "lesion", "spot", "yellow", "wilt")):
        return "symptom"
    if any(word in lowered for word in ("spray", "fungicide", "insecticide", "carbendazim")):
        return "chemical_option"
    if any(word in lowered for word in ("prevent", "prophyl", "resistant")):
        return "prevention"
    if any(word in lowered for word in ("biocontrol", "trichoderma", "pseudomonas")):
        return "biological_option"
    if any(word in lowered for word in ("remove", "destroy", "sanitation")):
        return "immediate_action"
    return "cultural_practice"


def main() -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)
    inventory = json.loads((PREVIOUS_AUDIT / "PDF_SOURCE_INVENTORY.json").read_text(encoding="utf-8"))
    extracted = json.loads((PREVIOUS_AUDIT / "SOURCE_EXTRACTION_REPORT.json").read_text(encoding="utf-8"))["items"]
    authority_by_hash = {row["sha256"]: row["apparent_official_status"] for row in inventory}
    source_registry = []
    for row in inventory:
        authority = row["apparent_official_status"]
        normalized_authority = {
            "OFFICIAL_GOVERNMENT_SOURCE": "OFFICIAL_GOVERNMENT",
            "OFFICIAL_UNIVERSITY_SOURCE": "OFFICIAL_UNIVERSITY",
            "OFFICIAL_RESEARCH_INSTITUTE_SOURCE": "OFFICIAL_RESEARCH_INSTITUTE",
        }.get(authority, "UNKNOWN_AUTHORITY")
        source_registry.append({
            "source_id": f"src_{row['sha256'][:16]}",
            "file_name": row["file_name"],
            "file_path": row["full_path"],
            "sha256": row["sha256"],
            "authority_class": normalized_authority,
            "issuing_organization": row["publisher"],
            "publication_title": row["title"],
            "publication_date": row["publication_year"],
            "official_status_evidence": (
                "Authority marker found inside extracted PDF text."
                if normalized_authority != "UNKNOWN_AUTHORITY"
                else "Authority not proven from PDF text."
            ),
            "crop_coverage": row["crops_covered"],
            "page_count": row["page_count"],
            "eligible_for_final_approval": normalized_authority != "UNKNOWN_AUTHORITY",
            "review_notes": "Authority classification requires human confirmation.",
        })
    dump(KNOWLEDGE / "sources/source_registry.json", source_registry)

    banana_doc = json.loads(BANANA_MAPPING.read_text(encoding="utf-8"))
    banana_labels = list(banana_doc["healthy_gate"]) + list(banana_doc["disease_classifier"])
    legacy_doc = json.loads(LEGACY_MAPPING.read_text(encoding="utf-8"))
    ordered = legacy_doc["ordered_classes"]
    registries = {
        "banana": registry(
            "banana", banana_labels, {"banana__healthy"}, BANANA_MODEL,
            BANANA_LOADER, BANANA_MAPPING,
        ),
        "paddy": registry(
            "paddy", [x for x in ordered if x.startswith(("paddy_", "rice_"))],
            {"paddy_healthy"}, LEGACY_MODEL, LEGACY_LOADER, LEGACY_MAPPING,
        ),
        "cotton": registry(
            "cotton", [x for x in ordered if x.startswith("cotton_")],
            {"cotton_healthy"}, LEGACY_MODEL, LEGACY_LOADER, LEGACY_MAPPING,
        ),
        "groundnut": registry(
            "groundnut", [x for x in ordered if x.startswith("groundnut_")],
            {"groundnut_healthy"}, LEGACY_MODEL, LEGACY_LOADER, LEGACY_MAPPING,
        ),
    }
    # Banana is a two-stage runtime. Preserve each head's native class index;
    # never pretend the two heads form one flat classifier.
    banana_head_labels = [
        ("healthy_gate", label, index, label == "banana__healthy")
        for label, index in banana_doc["healthy_gate"].items()
    ] + [
        ("disease_classifier", label, index, False)
        for label, index in banana_doc["disease_classifier"].items()
    ]
    registries["banana"]["labels"] = [
        {
            "classifier_head": head,
            "class_index": index,
            "runtime_label_exact": label,
            "normalized_lookup_key": normalized(label),
            "is_healthy": is_healthy,
            "is_unknown_or_background": False,
        }
        for head, label, index, is_healthy in banana_head_labels
    ]
    registries["banana"]["model_artifacts"] = [
        {
            "classifier_head": "healthy_gate",
            "path": "backend/app/banana_v3/artifacts/onnx/healthy_gate.onnx",
            "sha256": sha(ROOT / "backend/app/banana_v3/artifacts/onnx/healthy_gate.onnx"),
        },
        {
            "classifier_head": "disease_classifier",
            "path": str(BANANA_MODEL.relative_to(ROOT)),
            "sha256": sha(BANANA_MODEL),
        },
    ]
    for crop, document in registries.items():
        dump(KNOWLEDGE / f"runtime_labels/{crop}_runtime_labels.json", document)

    search_terms = {
        "banana__cordana_leaf_spot": ("cordana",),
        "banana__pestalotiopsis_leaf_spot": ("pestalotiopsis",),
        "banana__sigatoka_leaf_spot": ("sigatoka",),
        "rice_blast": ("blast",),
        "rice_brown_leaf_spot": ("brown leaf spot",),
        "rice_tungro": ("tungro",),
        "cotton_fusarium_wilt": ("fusarium wilt",),
        "cotton_verticillium_wilt": ("verticillium wilt",),
        "groundnut_rust": ("rust",),
    }
    packet_inventory = []
    authority_counts = {
        "OFFICIAL_GOVERNMENT_SOURCE": "official_government",
        "OFFICIAL_UNIVERSITY_SOURCE": "official_university",
        "OFFICIAL_RESEARCH_INSTITUTE_SOURCE": "official_research_institute",
        "UNKNOWN_AUTHORITY": "unknown_authority",
    }
    for crop, reg in registries.items():
        for label_row in reg["labels"]:
            label = label_row["runtime_label_exact"]
            terms = search_terms.get(label, ())
            candidates = []
            for item in extracted:
                excerpt = item["raw_source_excerpt"]
                if crop not in item["crop_context"] or not terms:
                    continue
                if not any(term in excerpt.lower() for term in terms):
                    continue
                authority = authority_by_hash[item["source_pdf_sha256"]]
                final_authority = authority != "UNKNOWN_AUTHORITY"
                candidates.append({
                    "text_original": excerpt,
                    "text_normalized": " ".join(excerpt.split()),
                    "field_type": field_type(excerpt),
                    "source_id": f"src_{item['source_pdf_sha256'][:16]}",
                    "source_file_name": item["source_file"],
                    "source_authority": authority.replace("_SOURCE", ""),
                    "page_number": item["pdf_page_index"] + 1,
                    "pdf_page_index": item["pdf_page_index"],
                    "section_heading": item["section_title"],
                    "exact_excerpt": excerpt,
                    "candidate_disease_mapping": label,
                    "mapping_confidence": "MEDIUM" if final_authority else "LOW",
                    "final_authority_eligible": final_authority,
                    "verification_status": "PENDING_HUMAN_REVIEW",
                    "verification_label": VERIFY,
                })
            counts = {value: 0 for value in authority_counts.values()}
            for candidate in candidates:
                key = authority_counts.get(
                    f"{candidate['source_authority']}_SOURCE",
                    "unknown_authority",
                )
                counts[key] += 1
            fields = {
                key: [candidate for candidate in candidates if candidate["field_type"] == key]
                for key in (
                    "symptom", "immediate_action", "prevention", "cultural_practice",
                    "biological_option", "chemical_option", "avoid_action",
                )
            }
            packet = {
                "crop_id": crop,
                "runtime_label_exact": label,
                "runtime_class_index": label_row["class_index"],
                "candidate_canonical_disease_name": None,
                "candidate_tamil_disease_name": None,
                "mapping_status": "PENDING_HUMAN_REVIEW",
                "authority_summary": counts,
                "candidate_fields": {
                    "symptoms": fields["symptom"],
                    "immediate_actions": fields["immediate_action"],
                    "prevention": fields["prevention"],
                    "cultural_practices": fields["cultural_practice"],
                    "biological_options": fields["biological_option"],
                    "chemical_options": fields["chemical_option"],
                    "avoid_actions": fields["avoid_action"],
                },
                "source_conflicts": [],
                "missing_fields": [
                    name for name, value in {
                        "symptoms": fields["symptom"],
                        "immediate_actions": fields["immediate_action"],
                        "prevention": fields["prevention"],
                    }.items() if not value
                ],
                "tamil_translation_status": "NOT_TRANSLATED",
                "human_approval_status": "PENDING",
                "healthy_treatment_blocked": label_row["is_healthy"],
            }
            packet_dir = KNOWLEDGE / "review_packets" / crop / normalized(label)
            dump(packet_dir / "packet.json", packet)
            dump(packet_dir / "candidates.json", candidates)
            dump(packet_dir / "conflicts.json", [])
            dump(packet_dir / "tamil_draft.json", {
                "status": "NOT_TRANSLATED", "items": [],
                "approval_status": "PENDING",
            })
            (packet_dir / "packet.md").write_text(
                f"# Review packet: `{label}`\n\n"
                f"- Crop: `{crop}`\n- Runtime class index: {label_row['class_index']}\n"
                f"- Candidate excerpts: {len(candidates)}\n"
                "- Mapping approval: PENDING_HUMAN_REVIEW\n"
                "- Tamil: NOT_TRANSLATED\n"
                f"- Warning: {VERIFY}\n",
                encoding="utf-8",
            )
            evidence_dir = packet_dir / "evidence"
            evidence_dir.mkdir(parents=True, exist_ok=True)
            for index, candidate in enumerate(candidates):
                evidence = evidence_dir / (
                    f"source_{candidate['source_id']}_page_{candidate['page_number']}_{index}.txt"
                )
                evidence.write_text(
                    candidate["exact_excerpt"] + f"\n\n{VERIFY}\n",
                    encoding="utf-8",
                )
            packet_inventory.append({
                "crop_id": crop, "runtime_label_exact": label,
                "candidate_count": len(candidates),
                "status": "REVIEW_PACKET_READY",
            })

    for folder in ("approved", "pending", "rejected", "conflicts", "tamil_review_queue"):
        (KNOWLEDGE / folder).mkdir(parents=True, exist_ok=True)
        readme = KNOWLEDGE / folder / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# {folder.replace('_', ' ').title()}\n\n"
                "Human decisions only. Automated tooling must not infer approval.\n",
                encoding="utf-8",
            )

    critical = [
        BANANA_MAPPING, BANANA_MODEL, BANANA_LOADER, LEGACY_MAPPING,
        LEGACY_MODEL, LEGACY_LOADER, PREVIOUS_AUDIT / "PDF_SOURCE_INVENTORY.json",
    ]
    evidence_inventory = [{
        "path": str(path),
        "purpose": "runtime/source evidence",
        "exists": path.exists(),
        "sha256": sha(path),
        "evidence_type": "runtime" if "backend" in path.parts else "generated",
        "used_for_decision": True,
    } for path in critical]
    dump(AUDIT / "runtime_evidence_inventory.json", evidence_inventory)
    dump(AUDIT / "repository_inventory.json", evidence_inventory)
    (AUDIT / "repository_inventory.md").write_text(
        "\n".join(f"- `{item['path']}` — `{item['sha256']}`" for item in evidence_inventory) + "\n",
        encoding="utf-8",
    )
    freeze = {
        "BANANA_RUNTIME_LABELS_FROZEN": "YES",
        "PADDY_RUNTIME_LABELS_FROZEN": "YES",
        "COTTON_RUNTIME_LABELS_FROZEN": "YES",
        "GROUNDNUT_RUNTIME_LABELS_FROZEN": "YES",
        "REDGRAM_RUNTIME_LABELS_FROZEN": "NO",
        "CHILLI_RUNTIME_LABELS_FROZEN": "NO",
    }
    dump(AUDIT / "runtime_label_freeze_report.json", freeze)
    (AUDIT / "runtime_label_freeze_report.md").write_text(
        "\n".join(f"{key}={value}" for key, value in freeze.items()) + "\n",
        encoding="utf-8",
    )
    dump(AUDIT / "review_packet_inventory.json", packet_inventory)
    (AUDIT / "review_packet_inventory.md").write_text(
        "\n".join(
            f"- {row['crop_id']} / `{row['runtime_label_exact']}`: "
            f"{row['candidate_count']} candidates"
            for row in packet_inventory
        ) + "\n",
        encoding="utf-8",
    )
    print(AUDIT)


if __name__ == "__main__":
    main()
