import json
from pathlib import Path

from scripts.evaluate_crop_release_readiness import REQUIRED_GATES, evaluate


def test_missing_manifest_fails_closed(tmp_path: Path) -> None:
    assert evaluate("chilli", tmp_path / "missing.json")["status"] == "NOT_READY"


def test_legacy_crop_cannot_be_promoted_by_code_alone(tmp_path: Path) -> None:
    assert evaluate("paddy", tmp_path / "missing.json")["status"] == "NOT_READY"


def test_missing_calibration_and_thresholds_block_release(tmp_path: Path) -> None:
    evidence = {"gates": {gate: True for gate in REQUIRED_GATES}}
    evidence["gates"]["calibration"] = None
    evidence["gates"]["thresholds_abstention"] = None
    path = tmp_path / "chilli.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    result = evaluate("chilli", path)
    assert result["status"] == "NOT_READY"
    assert not result["gates"]["calibration"]["passed"]
    assert not result["gates"]["thresholds_abstention"]["passed"]


def test_hash_mismatch_blocks_release(tmp_path: Path) -> None:
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"model")
    evidence = {"gates": {gate: True for gate in REQUIRED_GATES}}
    for gate in ("checkpoint", "class_mapping", "calibration", "thresholds_abstention", "onnx", "bundle"):
        evidence["gates"][gate] = {"path": str(artifact), "sha256": "0" * 64}
    evidence["gates"]["onnx"]["opset"] = 17
    path = tmp_path / "redgram.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    assert evaluate("redgram", path)["status"] == "NOT_READY"
