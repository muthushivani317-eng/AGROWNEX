"""Read-only Google Drive artifact audit for the legacy AgrowAI joint model."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

APPROVED_ROOTS = (Path("/content/drive/MyDrive/AgrowAI_V1"),)
OUTPUT = Path("/content/drive/MyDrive/AgrowAI_V1/audits/multi_crop_legacy_audit")
SUFFIXES = {".pt", ".pth", ".onnx", ".npz", ".json", ".jsonl", ".csv"}
NAME_MARKERS = ("manifest", "receipt", "temperature", "threshold", "calibration",
                "evaluation", "confusion", "training", "class_mapping",
                "split", "provisional", "runtime", "bundle", "lineage")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_json_summary(path: Path) -> dict:
    if path.suffix.lower() != ".json" or path.stat().st_size > 10_000_000:
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"json_error": type(exc).__name__}
    if not isinstance(value, dict):
        return {"json_type": type(value).__name__}
    keys = sorted(value)[:100]
    summary = {"keys": keys}
    for key in ("model_name", "model_version", "classes", "class_to_index",
                "split_counts", "temperature", "threshold", "status"):
        if key in value:
            summary[key] = value[key]
    return summary


def audit() -> dict:
    rows = []
    for root in APPROVED_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            lower = path.name.lower()
            if path.suffix.lower() not in SUFFIXES and not any(x in lower for x in NAME_MARKERS):
                continue
            stat = path.stat()
            rows.append({
                "path": str(path), "size_bytes": stat.st_size,
                "modified_time_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "sha256": digest(path), "json_summary": safe_json_summary(path),
            })
    conflicts = {}
    for row in rows:
        conflicts.setdefault(Path(row["path"]).name.lower(), []).append(row["sha256"])
    conflicting_names = {k: sorted(set(v)) for k, v in conflicts.items() if len(set(v)) > 1}
    return {
        "status": "AUDIT_ONLY_FAIL_CLOSED",
        "roots": [str(p) for p in APPROVED_ROOTS],
        "artifact_count": len(rows),
        "artifacts": rows,
        "conflicting_filenames": conflicting_names,
        "provisional_test_images_opened": False,
        "training_performed": False,
    }


if __name__ == "__main__":
    report = audit()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "legacy_joint_artifact_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("AGROWAI_LEGACY_JOINT_MODEL_AUDIT_COMPLETE")
