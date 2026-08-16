"""Fail-closed Chilli pipeline gate. No Banana artifacts are accepted."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

REQUIRED = ("archive", "licence", "class_mapping", "cleaned_manifest",
            "duplicate_audit", "split_manifest", "leakage_report")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("crop") != "chilli":
        raise RuntimeError("CHILLI_CROP_CONFIG_REQUIRED")
    checks = {}
    for name in REQUIRED:
        spec = config.get(name)
        if not isinstance(spec, dict) or not spec.get("path") or not spec.get("sha256"):
            raise RuntimeError(f"CHILLI_REQUIRED_INPUT_MISSING:{name}")
        path = Path(spec["path"])
        if not path.is_file() or sha(path) != spec["sha256"]:
            raise RuntimeError(f"CHILLI_INPUT_INTEGRITY_FAILURE:{name}")
        checks[name] = "VERIFIED"
    return {"crop": "chilli", "status": "CHILLI_INPUT_AUDIT_COMPLETE", "checks": checks}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit(Path(args.config))
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("CHILLI_INPUT_AUDIT_COMPLETE")
