from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pytest
from app.crop_runtime.bundle_installer import (
    BundleVerificationError,
    RedgramV2Expectations,
    inspect_archive,
    verify_redgram_v2_bundle,
)
from app.crop_runtime.registry import CropRegistry, load_registry
from app.crop_runtime.resolver import (
    ModelNotAvailableError,
    RuntimeIntegrityError,
    RuntimeResolver,
    required_runtime_files,
)
from app.crop_runtime.router import build_model_status, router
from app.crop_runtime.schemas import CropRegistryDocument
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _redgram_v2_expectations() -> RedgramV2Expectations:
    return RedgramV2Expectations(
        zip_sha256="e033b40da24144f25e07bf6f91470681b6f29d4edf3a364b1b87be16cff27c1f",
        checkpoint_sha256="2f766c519cbf016c7c3600c4ceb75419c49ce752f4b293119bdc54f93fb8129e",
        model_name="redgram_mobilenetv3_small_v2",
        supported_classes=(
            "redgram__healthy",
            "redgram__leaf_spot",
            "redgram__sterility_mosaic",
        ),
        temperature=2.193619697974462,
        class_gates={
            "redgram__healthy": {
                "confidence_threshold": 0.81,
                "margin_threshold": 0.0,
            },
            "redgram__leaf_spot": {
                "confidence_threshold": 0.97,
                "margin_threshold": 0.0,
            },
            "redgram__sterility_mosaic": {
                "confidence_threshold": 0.67,
                "margin_threshold": 0.0,
            },
        },
        fallback="ABSTAIN",
        field_validation_status=(
            "PUBLIC_DATASET_PROVISIONAL_PASSED_TN_FIELD_VALIDATION_PENDING"
        ),
    )


def _installed_redgram_v2() -> Path:
    return (
        Path(__file__).parents[1]
        / "model_artifacts"
        / "frozen_runtime"
        / "redgram_v2"
    )


def _runtime(
    root: Path,
    crop: str,
    *,
    model_name: str = "test",
    classes: list[str] | None = None,
    temperature: float = 1.0,
    class_specific_gates: dict[str, dict[str, float]] | None = None,
    fallback: str | None = None,
    thresholds_filename: str = "selected_thresholds.json",
) -> Path:
    runtime = root / "artifacts" / crop
    runtime.mkdir(parents=True, exist_ok=True)
    ordered_classes = classes or ["healthy"]
    payloads = {
        "best.pt": b"model",
        "class_to_index.json": json.dumps(
            {name: index for index, name in enumerate(ordered_classes)}
        ).encode(),
        "index_to_class.json": json.dumps(
            {str(index): name for index, name in enumerate(ordered_classes)}
        ).encode(),
        "preprocessing.json": b'{"image_size":224}',
        "temperature.json": json.dumps({"temperature": temperature}).encode(),
        thresholds_filename: json.dumps(
            {"class_specific_gates": class_specific_gates}
            if class_specific_gates is not None
            else {"confidence": 0.8}
        ).encode(),
        "abstention_policy.json": json.dumps(
            {"fallback": fallback} if fallback is not None else {"enabled": True}
        ).encode(),
        "runtime_config.json": json.dumps({"model_name": model_name}).encode(),
        "FROZEN_DECISION_RECORD.md": b"# Frozen",
    }
    for name, data in payloads.items():
        (runtime / name).write_bytes(data)
    lines = [
        f"{hashlib.sha256(data).hexdigest()}  {name}"
        for name, data in payloads.items()
    ]
    (runtime / "SHA256SUMS.txt").write_text("\n".join(lines), encoding="utf-8")
    assert all(
        (runtime / name).is_file()
        for name in required_runtime_files(thresholds_filename)
    )
    return runtime


def _registry(runtime_path: str = "artifacts/banana") -> CropRegistry:
    document = {
        "registry_schema_version": "1.0.0",
        "crops": [
            {
                "crop_id": "banana",
                "display_name_en": "Banana",
                "display_name_ta": "HUMAN_TRANSLATION_REVIEW_REQUIRED",
                "aliases": ["banana"],
                "model_status": "FROZEN_RUNTIME_READY",
                "runtime_path": runtime_path,
                "supported_classes": ["healthy"],
                "crop_enabled": True,
                "disease_detection_enabled": True,
                "advisory_enabled": False,
                "limitation_message_en": "Provisional.",
                "limitation_message_ta": "HUMAN_TRANSLATION_REVIEW_REQUIRED",
                "official_accuracy_claim": False,
                "field_validation_status": "NOT_STARTED",
                "last_verified_at": None,
                "registry_schema_version": "1.0.0",
            },
            {
                "crop_id": "coconut",
                "display_name_en": "Coconut",
                "display_name_ta": "HUMAN_TRANSLATION_REVIEW_REQUIRED",
                "aliases": ["coconut"],
                "model_status": "MODEL_NOT_COMPLETED",
                "runtime_path": None,
                "supported_classes": [],
                "crop_enabled": True,
                "disease_detection_enabled": False,
                "advisory_enabled": False,
                "limitation_message_en": "Not available.",
                "limitation_message_ta": "HUMAN_TRANSLATION_REVIEW_REQUIRED",
                "official_accuracy_claim": False,
                "field_validation_status": "NOT_STARTED",
                "last_verified_at": None,
                "registry_schema_version": "1.0.0",
            },
        ],
    }
    return CropRegistry(CropRegistryDocument.model_validate(document))


def test_initial_registry_validates_every_supported_status() -> None:
    registry = load_registry()
    statuses = {entry.model_status.value for entry in registry.document.crops}
    assert statuses == {
        "FROZEN_RUNTIME_READY",
        "MODEL_PIPELINE_PENDING",
        "MODEL_NOT_COMPLETED",
        "DATASET_UNRESOLVED",
        "LEGACY_JOINT_MODEL_AUDIT_REQUIRED",
    }
    assert all(entry.official_accuracy_claim is False for entry in registry.document.crops)


def test_unavailable_statuses_fail_closed() -> None:
    registry = load_registry()
    resolver = RuntimeResolver(registry, Path(__file__).parents[1])
    expected = {
        "coconut": "MODEL_NOT_COMPLETED",
        "blackgram": "DATASET_UNRESOLVED",
        "paddy": "LEGACY_JOINT_MODEL_AUDIT_REQUIRED",
    }
    for crop, status in expected.items():
        with pytest.raises(ModelNotAvailableError) as caught:
            resolver.resolve(crop)
        assert caught.value.response.limitation.value == status
        assert caught.value.response.official_accuracy_claim is False


def test_redgram_runtime_integrity_is_separate_from_deployment(tmp_path: Path) -> None:
    classes = [
        "redgram__healthy",
        "redgram__leaf_spot",
        "redgram__sterility_mosaic",
    ]
    gates = {
        "redgram__healthy": {
            "confidence_threshold": 0.81,
            "margin_threshold": 0.0,
        },
        "redgram__leaf_spot": {
            "confidence_threshold": 0.97,
            "margin_threshold": 0.0,
        },
        "redgram__sterility_mosaic": {
            "confidence_threshold": 0.67,
            "margin_threshold": 0.0,
        },
    }
    _runtime(
        tmp_path,
        "redgram",
        model_name="redgram_mobilenetv3_small_v2",
        classes=classes,
        temperature=2.193619697974462,
        class_specific_gates=gates,
        fallback="ABSTAIN",
        thresholds_filename="selected_class_specific_thresholds.json",
    )
    raw = load_registry().document.model_dump(mode="json")
    redgram = next(entry for entry in raw["crops"] if entry["crop_id"] == "redgram")
    redgram["model_version"] = "redgram_mobilenetv3_small_v2"
    redgram["deployment_status"] = "PROVISIONAL_RUNTIME_CANDIDATE"
    redgram["pilot_inference_eligible"] = True
    redgram["field_validation_status"] = (
        "PUBLIC_DATASET_PROVISIONAL_PASSED_TN_FIELD_VALIDATION_PENDING"
    )
    redgram["expected_temperature"] = 2.193619697974462
    redgram["expected_class_gates"] = gates
    redgram["thresholds_filename"] = "selected_class_specific_thresholds.json"
    redgram["runtime_path"] = "artifacts/redgram"
    redgram["checkpoint_sha256"] = hashlib.sha256(b"model").hexdigest()
    redgram["last_verified_at"] = None
    registry = CropRegistry(CropRegistryDocument.model_validate(raw))
    resolver = RuntimeResolver(registry, tmp_path)

    entry = registry.get("redgram")
    assert entry.model_status.value == "FROZEN_RUNTIME_READY"
    assert entry.model_version == "redgram_mobilenetv3_small_v2"
    assert entry.deployment_status == "PROVISIONAL_RUNTIME_CANDIDATE"
    assert entry.pilot_inference_eligible is True
    assert entry.general_farmer_inference_authorized is False
    assert entry.expert_verified is False
    assert entry.tamil_nadu_field_validated is False
    assert entry.disease_detection_enabled is False
    assert entry.official_accuracy_claim is False
    assert entry.supported_classes == classes
    assert entry.field_validation_status == (
        "PUBLIC_DATASET_PROVISIONAL_PASSED_TN_FIELD_VALIDATION_PENDING"
    )
    assert "v1" not in entry.model_version
    assert entry.limitation_message_ta == "HUMAN_TRANSLATION_REVIEW_REQUIRED"
    assert entry.display_name_ta == "HUMAN_TRANSLATION_REVIEW_REQUIRED"
    assert entry.last_verified_at is None
    assert resolver.verify_integrity("redgram").crop_id == "redgram"
    with pytest.raises(ModelNotAvailableError) as caught:
        resolver.resolve("redgram")
    assert caught.value.response.crop_id == "redgram"
    assert "Banana" not in caught.value.response.message_en
    assert "Chilli" not in caught.value.response.message_en


def test_redgram_missing_local_bundle_readiness_fails_closed(tmp_path: Path) -> None:
    registry = load_registry()
    redgram = registry.get("redgram")
    status = build_model_status(redgram, RuntimeResolver(registry, tmp_path))

    assert status == {
        "crop_id": "redgram",
        "declared_status": "FROZEN_RUNTIME_READY",
        "model_status": "FROZEN_RUNTIME_READY",
        "local_runtime_bundle_present": False,
        "local_integrity_verified": False,
        "local_runtime_ready": False,
        "integrity_status": "LOCAL_RUNTIME_BUNDLE_MISSING",
        "pilot_inference_eligible": True,
        "disease_detection_enabled": False,
        "general_farmer_inference_authorized": False,
        "technical_inference_ready": False,
        "field_validation_status": "RESTRICTED_INTERNAL_TESTING_ONLY",
        "official_accuracy_claim": False,
    }


def test_redgram_configuration_mismatch_fails_integrity_closed(
    tmp_path: Path,
) -> None:
    raw = load_registry().document.model_dump(mode="json")
    redgram = next(entry for entry in raw["crops"] if entry["crop_id"] == "redgram")
    redgram["runtime_path"] = "artifacts/redgram"
    redgram["checkpoint_sha256"] = hashlib.sha256(b"model").hexdigest()
    registry = CropRegistry(CropRegistryDocument.model_validate(raw))
    runtime = _runtime(
        tmp_path,
        "redgram",
        model_name=redgram["model_version"],
        classes=redgram["supported_classes"],
        temperature=9.0,
        class_specific_gates=redgram["expected_class_gates"],
        fallback="ABSTAIN",
        thresholds_filename=redgram["thresholds_filename"],
    )
    payload_names = [
        name
        for name in required_runtime_files(redgram["thresholds_filename"])
        if name != "SHA256SUMS.txt"
    ]
    (runtime / "SHA256SUMS.txt").write_text(
        "\n".join(
            f"{hashlib.sha256((runtime / name).read_bytes()).hexdigest()}  {name}"
            for name in payload_names
        ),
        encoding="utf-8",
    )

    resolver = RuntimeResolver(registry, tmp_path)
    with pytest.raises(RuntimeIntegrityError, match="temperature"):
        resolver.verify_integrity("redgram")
    status = build_model_status(registry.get("redgram"), resolver)
    assert status["local_runtime_bundle_present"] is True
    assert status["local_integrity_verified"] is False
    assert status["local_runtime_ready"] is False
    assert status["technical_inference_ready"] is False


def test_exact_installed_redgram_v2_bundle_passes_verification() -> None:
    report = verify_redgram_v2_bundle(
        _installed_redgram_v2(), _redgram_v2_expectations()
    )
    assert report["checkpoint_sha256"] == (
        "2f766c519cbf016c7c3600c4ceb75419c49ce752f4b293119bdc54f93fb8129e"
    )
    assert report["final_field_validation_status"] == (
        "PUBLIC_DATASET_PROVISIONAL_PASSED_TN_FIELD_VALIDATION_PENDING"
    )


def test_modified_installed_model_fails_bundle_verification(tmp_path: Path) -> None:
    candidate = tmp_path / "runtime"
    shutil.copytree(_installed_redgram_v2(), candidate)
    (candidate / "best.pt").write_bytes(b"modified")
    with pytest.raises(BundleVerificationError, match="manifest mismatch"):
        verify_redgram_v2_bundle(candidate, _redgram_v2_expectations())


def test_modified_installed_config_fails_bundle_verification(tmp_path: Path) -> None:
    candidate = tmp_path / "runtime"
    shutil.copytree(_installed_redgram_v2(), candidate)
    config = json.loads((candidate / "runtime_config.json").read_text("utf-8"))
    config["model_name"] = "not_redgram_v2"
    (candidate / "runtime_config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    with pytest.raises(BundleVerificationError, match="manifest mismatch"):
        verify_redgram_v2_bundle(candidate, _redgram_v2_expectations())


def test_missing_internal_sha_manifest_fails_bundle_verification(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "runtime"
    shutil.copytree(_installed_redgram_v2(), candidate)
    (candidate / "SHA256SUMS.txt").unlink()
    with pytest.raises(BundleVerificationError, match="manifest"):
        verify_redgram_v2_bundle(candidate, _redgram_v2_expectations())


def test_path_traversal_archive_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "traversal.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("deployment_candidate_bundle/../escape.txt", "blocked")
    with pytest.raises(BundleVerificationError, match="traversal"):
        inspect_archive(archive)


def test_runtime_resolves_only_its_crop(tmp_path: Path) -> None:
    _runtime(tmp_path, "banana")
    resolver = RuntimeResolver(_registry(), tmp_path)
    banana = resolver.resolve("banana")
    assert banana.crop_id == "banana"
    assert banana.abstention_policy == {"enabled": True}
    with pytest.raises(ModelNotAvailableError):
        resolver.resolve("coconut")


def test_chilli_resolves_only_to_chilli_runtime(tmp_path: Path) -> None:
    _runtime(tmp_path, "chilli")
    raw = _registry().document.model_dump(mode="json")
    chilli = raw["crops"][0].copy()
    chilli.update(
        {
            "crop_id": "chilli",
            "display_name_en": "Chilli",
            "aliases": ["chilli"],
            "runtime_path": "artifacts/chilli",
        }
    )
    raw["crops"].append(chilli)
    resolver = RuntimeResolver(
        CropRegistry(CropRegistryDocument.model_validate(raw)), tmp_path
    )
    assert resolver.resolve("chilli").root == (tmp_path / "artifacts" / "chilli")
    assert resolver.resolve("chilli").root != (tmp_path / "artifacts" / "banana")


def test_missing_sums_and_hash_mismatch_block_loading(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, "banana")
    resolver = RuntimeResolver(_registry(), tmp_path)
    (runtime / "SHA256SUMS.txt").unlink()
    with pytest.raises(RuntimeIntegrityError, match="missing"):
        resolver.resolve("banana")
    _runtime(tmp_path, "banana")
    (runtime / "best.pt").write_bytes(b"tampered")
    with pytest.raises(RuntimeIntegrityError, match="hash mismatch"):
        resolver.resolve("banana")
    status = build_model_status(resolver.registry.get("banana"), resolver)
    assert status["local_runtime_bundle_present"] is True
    assert status["local_integrity_verified"] is False
    assert status["local_runtime_ready"] is False
    assert status["technical_inference_ready"] is False


def test_sealed_test_path_is_never_accessed(tmp_path: Path) -> None:
    registry = _registry("provisional_test/banana")
    resolver = RuntimeResolver(registry, tmp_path)
    with pytest.raises(RuntimeIntegrityError, match="sealed test"):
        resolver.resolve("banana")


def test_redgram_consumed_provisional_test_path_is_rejected_before_file_access(
    tmp_path: Path,
) -> None:
    raw = load_registry().document.model_dump(mode="json")
    redgram = next(entry for entry in raw["crops"] if entry["crop_id"] == "redgram")
    redgram["runtime_path"] = "consumed_provisional_test/redgram"
    resolver = RuntimeResolver(
        CropRegistry(CropRegistryDocument.model_validate(raw)), tmp_path
    )
    with pytest.raises(RuntimeIntegrityError, match="sealed test"):
        resolver.verify_integrity("redgram")
    assert not (tmp_path / "consumed_provisional_test").exists()


def test_invalid_crop_id_and_public_path_redaction() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.get("/crops/not-a-crop").status_code == 404
    crops = client.get("/crops").json()
    assert crops
    assert all("runtime_path" not in crop for crop in crops)
    assert all("checkpoint_sha256" not in crop for crop in crops)
    assert all("architecture" not in crop for crop in crops)
    assert all("supported_classes" not in crop for crop in crops)
    assert all("deployment_zip_sha256" not in crop for crop in crops)
    assert all("expected_temperature" not in crop for crop in crops)
    assert all("expected_class_gates" not in crop for crop in crops)
    assert all("pilot_inference_eligible" not in crop for crop in crops)
    assert all(crop["official_accuracy_claim"] is False for crop in crops)
    redgram = next(crop for crop in crops if crop["crop_id"] == "redgram")
    assert redgram["model_status"] == "FROZEN_RUNTIME_READY"
    assert redgram["disease_detection_enabled"] is False
    assert redgram["field_validation_status"] == "RESTRICTED_INTERNAL_TESTING_ONLY"
    assert "general farmer diagnosis remains blocked" in redgram["limitation_message_en"]
    serialized = json.dumps(redgram)
    assert "0.9302325581395349" not in serialized
    assert "0.9332591768631814" not in serialized
    registry = load_registry()
    assert registry.get("coconut").model_status.value == "MODEL_NOT_COMPLETED"
    assert registry.get("blackgram").model_status.value == "DATASET_UNRESOLVED"


def test_internal_readiness_is_verified_but_redacts_sensitive_runtime_data() -> None:
    app = FastAPI()
    app.include_router(router)
    statuses = TestClient(app).get("/models/status").json()
    redgram = next(item for item in statuses if item["crop_id"] == "redgram")
    assert redgram["local_runtime_bundle_present"] is True
    assert redgram["local_integrity_verified"] is True
    assert redgram["local_runtime_ready"] is True
    assert redgram["runtime_loadable"] is True
    assert redgram["classification"] == "INTERNAL_TEST_READY"
    assert redgram["pilot_inference_eligible"] is True
    chilli = next(item for item in statuses if item["crop_id"] == "chilli")
    assert chilli["pilot_inference_eligible"] is True
    assert redgram["technical_testing_eligible"] is True
    serialized = json.dumps(redgram)
    for forbidden in (
        "runtime_path",
        "checkpoint_sha256",
        "deployment_zip_sha256",
        "2.193619697974462",
        "0.97",
        "model_artifacts",
    ):
        assert forbidden not in serialized
