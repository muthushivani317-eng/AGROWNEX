"""Build non-approving crop-ID and recommendation review material from existing evidence."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import os
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "datasets/crop_identity_v2"
STAMP = os.environ.get("AGROWAI_REPORT_STAMP") or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
REPORT = ROOT / "reports/crop_id_data_acquisition_and_review" / STAMP
NOTICE = "INTERNAL NON-EXPERT REVIEW ONLY\nOFFICIAL AGRICULTURAL EXPERT VERIFICATION NOT COMPLETED"


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build_image_review() -> tuple[list[dict], dict]:
    for name in ("downloads", "raw", "quarantine", "rejected", "manifests", "review_packets"):
        (V2 / name).mkdir(parents=True, exist_ok=True)
    sources = [
        ("chilli", ROOT / "datasets/crop_id_sources/chilli/bangladesh_chilli_w9mr3vf56s_v1/manifests/screening_manifest.csv"),
        ("chilli", ROOT / "datasets/crop_id_sources/chilli/jnucls_sbjykmmz4s_v1/manifests/screening_manifest.csv"),
    ]
    rows: list[dict] = []
    for crop, manifest in sources:
        source_root = manifest.parents[1] / "extracted_originals"
        for row in read_csv(manifest):
            decision = row.get("final_screening_decision", "")
            rows.append({
                "image_id": row["sha256"][:24],
                "proposed_class": crop,
                "source_dataset": row["source_id"],
                "original_path": str(source_root / row["source_path"]),
                "sha256": row["sha256"],
                "perceptual_hash": row.get("perceptual_hash", ""),
                "duplicate_family_id": row.get("duplicate_family_id", ""),
                "resolution": f"{row.get('width','')}x{row.get('height','')}",
                "quality_warnings": row.get("uncertainty_reason", ""),
                "licence_status": row.get("licence_state", ""),
                "original_or_augmented": "ORIGINAL_CANDIDATE",
                "source_screening_decision": decision,
                "suggested_reviewer_decision": (
                    "APPROVE" if decision == "CROP_ID_CLEAR_ACCEPT" else
                    "REJECT_DUPLICATE" if decision == "CROP_ID_EXCLUDE_DUPLICATE" else
                    "REJECT_WRONG_CLASS" if decision == "CROP_ID_EXCLUDE_PRODUCT_OR_FOOD_IMAGE" else
                    "QUARANTINE_UNCERTAIN"
                ),
                "reviewer_decision": "",
                "reviewer_notes": "",
                "notice": NOTICE,
            })
    red_root = ROOT / "datasets/crop_id_sources/redgram/wikimedia_commons_cajanus_cajan_20260730"
    state = json.loads((red_root / "metadata/download_state.json").read_text(encoding="utf-8"))
    by_name = {p.name: p for p in (red_root / "extracted_originals").rglob("*") if p.is_file()}
    for item in state:
        name = Path(item.get("expected_filename") or "").name
        path = by_name.get(name)
        if not path:
            continue
        rows.append({
            "image_id": sha256(path)[:24], "proposed_class": "redgram",
            "source_dataset": "wikimedia_commons_cajanus_cajan_20260730",
            "original_path": str(path), "sha256": sha256(path),
            "perceptual_hash": "PENDING", "duplicate_family_id": "PENDING",
            "resolution": "PENDING_VALIDATION", "quality_warnings": "MANUAL_CROP_AND_PRIVACY_REVIEW_REQUIRED",
            "licence_status": item.get("licence", "LICENCE_UNVERIFIED_DO_NOT_USE"),
            "original_or_augmented": "ORIGINAL_CANDIDATE", "source_screening_decision": "QUARANTINE_UNCERTAIN",
            "suggested_reviewer_decision": "QUARANTINE_UNCERTAIN",
            "reviewer_decision": "", "reviewer_notes": "", "notice": NOTICE,
        })
    fields = list(rows[0])
    out = V2 / "manifests/candidate_review_manifest.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    counts = {crop: {"downloaded": 0, "extracted": 0, "decodable": 0, "original_candidates": 0,
                     "augmented_candidates": 0, "duplicate_candidates": 0, "quarantined": 0,
                     "rejected": 0, "awaiting_human_review": 0, "approved": 0}
              for crop in ("banana","paddy","cotton","groundnut","chilli","redgram","unknown_crop","non_plant")}
    for row in rows:
        c = counts[row["proposed_class"]]
        c["downloaded"] += 1; c["extracted"] += 1; c["decodable"] += 1
        c["original_candidates"] += 1; c["awaiting_human_review"] += 1
        decision = row["source_screening_decision"]
        if "DUPLICATE" in decision:
            c["duplicate_candidates"] += 1; c["rejected"] += 1
        elif "EXCLUDE" in decision:
            c["rejected"] += 1
        elif "QUARANTINE" in decision:
            c["quarantined"] += 1
    for crop in counts:
        subset = [r for r in rows if r["proposed_class"] == crop]
        body = "\n".join(
            f'<tr><td><img loading="lazy" src="file:///{html.escape(r["original_path"].replace(chr(92), "/"))}"></td>'
            f'<td>{html.escape(r["source_dataset"])}</td><td>{html.escape(r["sha256"])}</td>'
            f'<td>{html.escape(r["quality_warnings"])}</td><td><select><option></option>'
            + "".join(f'<option>{x}</option>' for x in ("APPROVE","REJECT_WRONG_CLASS","REJECT_NON_PLANT","REJECT_LOW_QUALITY","REJECT_DUPLICATE","REJECT_AUGMENTED","REJECT_LICENCE","REJECT_PRIVACY","QUARANTINE_UNCERTAIN"))
            + '</select></td><td><textarea></textarea></td></tr>' for r in subset)
        page = f"<!doctype html><meta charset=utf-8><title>{crop} review</title><style>img{{max-width:160px;max-height:120px}}td{{vertical-align:top}}</style><h1>{crop}</h1><pre>{NOTICE}</pre><table><tr><th>thumbnail</th><th>source</th><th>sha256</th><th>warnings</th><th>decision</th><th>notes</th></tr>{body}</table>"
        (V2 / f"review_packets/{crop}.html").write_text(page, encoding="utf-8")
    dump(V2 / "manifests/class_counts.json", counts)
    return rows, counts


def build_recommendation_packets() -> list[dict]:
    extraction = json.loads((ROOT / "docs/model_audits/six_crop_recommendation_knowledge_and_integration/20260730T103944Z/SOURCE_EXTRACTION_REPORT.json").read_text(encoding="utf-8"))["items"]
    labels = {}
    for crop in ("chilli", "redgram"):
        path = ROOT / f"backend/model_artifacts/frozen_runtime/{crop}_mobilenetv3_small_v1_restricted/config/class_to_index.json"
        labels[crop] = list(json.loads(path.read_text(encoding="utf-8")).keys())
    index = []
    for crop, crop_labels in labels.items():
        for label in crop_labels:
            terms = [x for x in label.replace(f"{crop}__", "").split("_") if x not in {"healthy"}]
            candidates = []
            for item in extraction:
                excerpt = item["raw_source_excerpt"]
                if not terms or crop not in item["crop_context"] or not all(t in excerpt.lower() for t in terms[:2]):
                    continue
                candidates.append({"source_id": f"src_{item['source_pdf_sha256'][:16]}", "source_filename": item["source_file"],
                                   "printed_page": item["pdf_page_index"] + 1, "pdf_page_index": item["pdf_page_index"],
                                   "exact_relevant_passage": excerpt, "verification": "VERIFY AGAINST OFFICIAL SOURCE"})
            packet = {"crop": crop, "exact_runtime_label": label, "candidate_canonical_disease": None,
                      "official_english_disease_name": None, "candidate_tamil_disease_name": None,
                      "candidate_evidence": candidates, "symptom_candidate": [], "immediate_action_candidate": [],
                      "prevention_candidate": [], "cultural_control_candidate": [], "biological_control_candidate": [],
                      "chemical_control_candidate": [], "safety_note_candidate": ["VERIFY AGAINST OFFICIAL SOURCE"],
                      "conflict_notes": [], "english_draft": None, "tamil_draft": None,
                      "tamil_status": "AGRICULTURAL_REVIEW_REQUIRED", "reviewer_status": "PENDING_HUMAN_REVIEW",
                      "notice": NOTICE}
            target = ROOT / f"recommendation_knowledge/review_packets/{crop}/{label}"
            dump(target / "packet.json", packet)
            (target / "packet.md").write_text(f"# {label}\n\n{NOTICE}\n\nCandidate passages: {len(candidates)}\n\nVERIFY AGAINST OFFICIAL SOURCE\n", encoding="utf-8")
            index.append({"crop": crop, "runtime_label": label, "candidate_passages": len(candidates), "path": str((target / 'packet.json').relative_to(ROOT)), "status": "PENDING_HUMAN_REVIEW"})
    return index


def main() -> None:
    rows, counts = build_image_review()
    recs = build_recommendation_packets()
    REPORT.mkdir(parents=True, exist_ok=True)
    dump(REPORT / "IMAGE_INVENTORY.json", {"rows": len(rows), "per_class": counts})
    dump(REPORT / "REVIEW_PACKET_INDEX.json", [{"class": c, "path": f"datasets/crop_identity_v2/review_packets/{c}.html", "rows": v["awaiting_human_review"]} for c,v in counts.items()])
    dump(REPORT / "RECOMMENDATION_PACKET_INDEX.json", recs)
    print(f"REPORT_DIR={REPORT}")


if __name__ == "__main__":
    main()
