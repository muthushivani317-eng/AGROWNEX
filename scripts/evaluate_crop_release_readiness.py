"""Fail-closed evidence gate for AgrowAI crop diagnosis releases."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {"paddy", "cotton", "groundnut", "chilli", "redgram"}
REQUIRED_GATES = (
    "approved_manifest", "split_manifest", "leakage_report", "checkpoint",
    "class_mapping", "calibration", "thresholds_abstention", "onnx",
    "onnx_parity", "bundle", "backend_health_endpoint", "app_adapter",
    "tests", "field_validation_in_progress",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_artifact(spec: Any) -> tuple[bool, str]:
    if not isinstance(spec, dict):
        return False, "missing artifact specification"
    raw_path, expected = spec.get("path"), spec.get("sha256")
    if not raw_path or not expected:
        return False, "path or SHA-256 missing"
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        return False, f"missing file: {path}"
    if sha256(path) != expected:
        return False, f"SHA-256 mismatch: {path}"
    return True, "verified"


def evaluate(crop: str, evidence_path: Path | None = None) -> dict[str, Any]:
    canonical = "paddy" if crop == "rice" else crop
    if canonical not in SUPPORTED:
        return {"crop": canonical, "status": "NOT_READY", "gates": {},
                "errors": ["unsupported crop"]}
    path = evidence_path or ROOT / "docs" / "model_audits" / "evidence" / f"{canonical}.json"
    if not path.is_file():
        return {"crop": canonical, "status": "NOT_READY", "evidence_path": str(path),
                "gates": {}, "errors": ["machine-readable evidence manifest missing"]}
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"crop": canonical, "status": "NOT_READY", "evidence_path": str(path),
                "gates": {}, "errors": [f"invalid evidence manifest: {exc}"]}
    gates: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    artifacts = {"checkpoint", "class_mapping", "calibration", "thresholds_abstention", "onnx", "bundle"}
    for name in REQUIRED_GATES:
        value = evidence.get("gates", {}).get(name)
        if name in artifacts:
            passed, reason = check_artifact(value)
        else:
            passed, reason = value is True, "passed" if value is True else "missing or false"
        if name == "onnx" and passed and value.get("opset") != 17:
            passed, reason = False, "ONNX opset must equal 17"
        gates[name] = {"passed": passed, "reason": reason}
        if not passed:
            errors.append(f"{name}: {reason}")
    status = "AVAILABLE_FIELD_VALIDATION_IN_PROGRESS" if not errors else "NOT_READY"
    return {"crop": canonical, "status": status, "evidence_path": str(path),
            "gates": gates, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop", required=True)
    parser.add_argument("--evidence")
    parser.add_argument("--report")
    args = parser.parse_args()
    result = evaluate(args.crop.lower(), Path(args.evidence) if args.evidence else None)
    report = Path(args.report) if args.report else ROOT / "docs" / "model_audits" / f"{args.crop.lower()}_readiness.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if result["status"] == "AVAILABLE_FIELD_VALIDATION_IN_PROGRESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
