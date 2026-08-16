import json
from pathlib import Path

from notebooks.agrowai_legacy_joint_recovery import run


def test_recovery_fails_closed_and_writes_all_reports(tmp_path: Path) -> None:
    receipt = tmp_path / "one_time_evaluation_receipt.json"
    receipt.write_text(json.dumps({
        "provisional_test_opened": True,
        "evaluation_completed": True,
        "checkpoint_sha256": "f" * 64,
    }), encoding="utf-8")
    metrics = tmp_path / "provisional_test_metrics.json"
    metrics.write_text(json.dumps({"status": "historical_provisional"}), encoding="utf-8")
    audit = tmp_path / "legacy_joint_artifact_audit.json"
    audit.write_text(json.dumps({
        "artifacts": [{"path": str(receipt)}, {"path": str(metrics)}],
    }), encoding="utf-8")
    output = tmp_path / "recovery"

    decision = run(audit, output)

    assert decision["primary_decision"] == "LINEAGE_AMBIGUOUS"
    assert decision["provisional_results_used_for_selection_or_tuning"] is False
    assert decision["provisional_test_images_opened"] is False
    assert decision["training_or_model_modification_performed"] is False
    assert {
        "legacy_joint_lineage_report.json",
        "legacy_joint_lineage_report.md",
        "checkpoint_comparison.json",
        "receipt_crosscheck.json",
        "calibration_artifact_inventory.json",
        "onnx_lineage_report.json",
        "recovery_decision.json",
    } == {path.name for path in output.iterdir()}


def test_artifact_audit_does_not_discover_unlisted_provisional_images(tmp_path: Path) -> None:
    image = tmp_path / "provisional_test_image.jpg"
    image.write_bytes(b"must-not-open")
    audit = tmp_path / "legacy_joint_artifact_audit.json"
    audit.write_text('{"artifacts":[]}', encoding="utf-8")
    output = tmp_path / "recovery"

    run(audit, output)

    assert image.read_bytes() == b"must-not-open"
