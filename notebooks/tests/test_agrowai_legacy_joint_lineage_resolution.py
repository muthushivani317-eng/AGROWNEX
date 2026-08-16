from pathlib import Path

import notebooks.agrowai_legacy_joint_lineage_resolution as resolver


def decision(**overrides):
    values = {
        "target_checkpoint_found": True,
        "dev_linked": True,
        "calibration_linked": True,
        "receipt_linked": True,
        "runtime_linked": True,
        "mapping_ok": True,
        "onnx_origin_proven": True,
        "onnx_metadata_ok": True,
        "standalone_temperature": True,
        "standalone_thresholds": True,
    }
    values.update(overrides)
    return resolver.make_decision(**values)


def test_checkpoint_proven_but_onnx_origin_unknown_requires_reexport() -> None:
    result = decision(onnx_origin_proven=False)
    assert result["primary_decision"] == "REQUIRES_ONNX_REEXPORT"
    assert result["checkpoint_lineage_proven"] is True


def test_missing_temperature_uses_existing_calibration_split() -> None:
    assert decision(standalone_temperature=False)["primary_decision"] == (
        "READY_FOR_RECALIBRATION_FROM_EXISTING_CALIBRATION_SPLIT"
    )


def test_missing_thresholds_requires_calibration_only_reconstruction() -> None:
    assert decision(standalone_thresholds=False)["primary_decision"] == (
        "READY_FOR_THRESHOLD_RECONSTRUCTION_FROM_EXISTING_CALIBRATION_SPLIT"
    )


def test_checkpoint_link_failure_is_genuine_lineage_ambiguity() -> None:
    assert decision(dev_linked=False)["primary_decision"] == "LINEAGE_AMBIGUOUS"


def test_discovery_is_narrow_and_excludes_banana(tmp_path: Path, monkeypatch) -> None:
    allowed = tmp_path / "checkpoints/mobilenetv3_small_v1"
    allowed.mkdir(parents=True)
    legacy = allowed / "best.pt"
    legacy.write_bytes(b"legacy")
    banana = allowed / "banana_v3_best.pt"
    banana.write_bytes(b"banana")
    outside = tmp_path / "other/model.pt"
    outside.parent.mkdir()
    outside.write_bytes(b"outside")
    monkeypatch.setattr(resolver, "ALLOWED_ROOTS", (allowed,))
    monkeypatch.setattr(resolver, "ALLOWED_SINGLE_FILES", ())

    assert resolver.discover() == [legacy]


def test_receipt_hash_verification_never_opens_images(tmp_path: Path) -> None:
    result_file = tmp_path / "provisional_test_metrics.json"
    result_file.write_text("{}", encoding="utf-8")
    image = tmp_path / "provisional_image.jpg"
    image.write_bytes(b"sealed")
    receipt = {"result_sha256": resolver.sha256(result_file), "image_sha256": resolver.sha256(image)}

    result = resolver.verify_result_receipt(receipt, [result_file, image])

    assert result["image_files_opened"] is False
    assert resolver.sha256(image) in result["unresolved_recorded_hashes"]
    assert image.read_bytes() == b"sealed"
