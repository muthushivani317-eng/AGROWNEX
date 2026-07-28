from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.crop_runtime.registry import CropRegistry, load_registry
from app.crop_runtime.resolver import (
    REQUIRED_RUNTIME_FILES,
    ModelNotAvailableError,
    RuntimeIntegrityError,
    RuntimeResolver,
)
from app.crop_runtime.router import build_model_status, router
from app.crop_runtime.schemas import CropRegistryDocument
from app.modules.auth.dependencies import get_current_user
from app.modules.disease.dependencies import get_disease_service
from app.modules.disease.router import router as disease_router


def _runtime(root: Path, crop: str) -> Path:
    runtime = root / "artifacts" / crop
    runtime.mkdir(parents=True, exist_ok=True)
    payloads = {
        "best.pt": b"model",
        "class_to_index.json": b'{"healthy":0}',
        "index_to_class.json": b'{"0":"healthy"}',
        "preprocessing.json": b'{"image_size":224}',
        "temperature.json": b'{"temperature":1.0}',
        "selected_thresholds.json": b'{"confidence":0.8}',
        "abstention_policy.json": b'{"enabled":true}',
        "runtime_config.json": b'{"model":"test"}',
        "FROZEN_DECISION_RECORD.md": b"# Frozen",
    }
    for name, data in payloads.items():
        (runtime / name).write_bytes(data)
    lines = [
        f"{hashlib.sha256(data).hexdigest()}  {name}"
        for name, data in payloads.items()
    ]
    (runtime / "SHA256SUMS.txt").write_text("\n".join(lines), encoding="utf-8")
    assert all((runtime / name).is_file() for name in REQUIRED_RUNTIME_FILES)
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
    _runtime(tmp_path, "redgram")
    raw = load_registry().document.model_dump(mode="json")
    redgram = next(entry for entry in raw["crops"] if entry["crop_id"] == "redgram")
    redgram["runtime_path"] = "artifacts/redgram"
    registry = CropRegistry(CropRegistryDocument.model_validate(raw))
    resolver = RuntimeResolver(registry, tmp_path)

    entry = registry.get("redgram")
    assert entry.model_status.value == "FROZEN_RUNTIME_READY"
    assert entry.model_version == "redgram_mobilenetv3_small_v1"
    assert entry.checkpoint_sha256 == (
        "c9d289e688042fe67018b7462121cd288af51f023166505359bcd0b613f09843"
    )
    assert entry.disease_detection_enabled is False
    assert entry.official_accuracy_claim is False
    assert entry.supported_classes == [
        "redgram__healthy",
        "redgram__leaf_spot",
        "redgram__sterility_mosaic",
    ]
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
        "disease_detection_enabled": False,
        "inference_authorized": False,
        "official_accuracy_claim": False,
    }


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
    assert all(crop["official_accuracy_claim"] is False for crop in crops)
    redgram = next(crop for crop in crops if crop["crop_id"] == "redgram")
    assert redgram["model_status"] == "FROZEN_RUNTIME_READY"
    assert redgram["disease_detection_enabled"] is False
    assert "local runtime bundle has not been verified" in redgram["limitation_message_en"]


def test_disease_analyze_refuses_redgram_before_service_call() -> None:
    app = FastAPI()
    app.include_router(disease_router)
    service = Mock()
    service.analyze = AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: Mock(id="test-user")
    app.dependency_overrides[get_disease_service] = lambda: service
    response = TestClient(app).post(
        "/disease/analyze",
        json={
            "image_base64": "0123456789abcdef",
            "mime_type": "image/jpeg",
            "crop": "redgram",
        },
    )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "MODEL_NOT_AVAILABLE"
    assert detail["crop_id"] == "redgram"
    assert detail["official_accuracy_claim"] is False
    service.analyze.assert_not_awaited()
