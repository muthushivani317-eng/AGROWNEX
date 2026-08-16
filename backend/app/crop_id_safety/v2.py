"""Integrity-verified v2 OOD gate. It remains fail-closed until evidence is sufficient."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2] / "model_artifacts" / "safety_gates" / "crop_id_v2"


class SafetyGateV2Error(RuntimeError):
    pass


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_v2(root: Path = ROOT) -> dict[str, Any]:
    manifest_path = root / "integrity_manifest.json"
    if not manifest_path.is_file():
        raise SafetyGateV2Error("V2_INTEGRITY_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "gate_config.json",
        "feature_extractor_reference.json",
        "distance_policy.json",
        "threshold_policy.json",
        "category_policy.json",
        "source_manifest_hashes.json",
        "dataset_manifest_hashes.json",
        "rollback_metadata.json",
        "README.md",
    }
    if set(manifest) != required:
        raise SafetyGateV2Error("V2_ARTIFACT_SET_INVALID")
    for name, expected in manifest.items():
        path = root / name
        if not path.is_file() or _digest(path) != expected:
            raise SafetyGateV2Error("V2_ARTIFACT_INTEGRITY_FAILURE")
    config = json.loads((root / "gate_config.json").read_text(encoding="utf-8"))
    if (
        config.get("safety_gate_id") != "crop_id_safety_gate_v2"
        or config.get("version") != "2.0.0-internal"
        or config.get("general_farmer_release") != "BLOCKED"
        or config.get("default_outcome") != "OOD_UNCERTAIN"
        or config.get("prototype_status") != "INSUFFICIENT_INDEPENDENT_DATA"
    ):
        raise SafetyGateV2Error("V2_POLICY_INVALID")
    return config


def assess_v2(config: dict[str, Any]) -> dict[str, str]:
    """Do not authorize inference until frozen prototypes and thresholds exist."""
    return {
        "outcome": config["default_outcome"],
        "reason_code": "V2_INDEPENDENT_EVIDENCE_INSUFFICIENT",
        "gate_version": config["version"],
    }
