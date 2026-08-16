"""Railway environment and sanitized restricted-runtime readiness tests."""
from __future__ import annotations

import json
from pathlib import Path

import app.api.probes as probes
import pytest
from app.core.config import Settings
from app.crop_runtime.inventory import refresh_model_inventory
from app.crop_runtime.readiness import ReadinessResolver
from app.crop_runtime.registry import load_registry
from app.restricted_crops import integrity
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = BACKEND_ROOT / "model_artifacts" / "frozen_runtime"


def test_app_env_alias_selects_production(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    assert Settings(_env_file=None).environment == "production"


@pytest.mark.parametrize(
    "crop_id", ["banana", "redgram", "chilli"]
)
def test_repository_runtime_is_verified_and_loadable(crop_id: str):
    result = ReadinessResolver(load_registry(), BACKEND_ROOT).resolve(crop_id)

    assert result.artifact_present is True
    assert result.integrity_verified is True
    assert result.runtime_loadable is True
    assert result.readiness_reason == "ready"


@pytest.mark.parametrize("crop_id", ["paddy", "cotton", "groundnut"])
def test_legacy_joint_runtime_is_loadable_without_granting_release_authorization(
    crop_id: str,
):
    result = ReadinessResolver(load_registry(), BACKEND_ROOT).resolve(crop_id)

    assert result.artifact_present is True
    assert result.integrity_verified is True
    assert result.runtime_loadable is True
    assert result.readiness_reason == "ready"
    assert result.classification == "APP_INTEGRATED_TESTING_BLOCKED"
    assert result.general_farmer_inference_authorized is False


@pytest.mark.parametrize(
    ("integrity_code", "expected_reason"),
    [
        ("RUNTIME_PACKAGE_MISSING", "file_missing"),
        ("MANIFEST_FILE_MISSING", "file_missing"),
        ("SHA256_MANIFEST_MISSING", "manifest_missing"),
        ("PACKAGE_HASH_MISMATCH", "hash_mismatch"),
    ],
)
def test_restricted_runtime_failures_are_sanitized(
    monkeypatch, integrity_code: str, expected_reason: str
):
    def fail_closed(_crop_id: str):
        raise integrity.RestrictedRuntimeIntegrityError(integrity_code)

    monkeypatch.setattr(integrity, "verify_restricted_package", fail_closed)

    result = ReadinessResolver(load_registry(), BACKEND_ROOT).resolve("redgram")

    assert result.runtime_loadable is False
    assert result.readiness_reason == expected_reason
    assert str(BACKEND_ROOT) not in json.dumps(result.public_dict())


def test_public_readiness_exposes_only_sanitized_runtime_reason(monkeypatch):
    class Result:
        runtime_loadable = False
        readiness_reason = "manifest_missing"

    async def dependency_ready():
        return True

    monkeypatch.setattr(probes, "_check_db", dependency_ready)
    monkeypatch.setattr(probes, "_check_redis", dependency_ready)
    monkeypatch.setattr(ReadinessResolver, "resolve", lambda self, crop_id: Result())
    refresh_model_inventory()

    app = FastAPI()
    app.include_router(probes.router)
    response = TestClient(app).get("/ready")
    body = response.json()

    assert response.status_code == 503
    assert body["runtime_diagnostics"] == {
        "redgram": "manifest_missing",
        "chilli": "manifest_missing",
    }
    serialized = json.dumps(body)
    assert str(BACKEND_ROOT) not in serialized
    assert "checkpoint" not in serialized
    assert "sha256" not in serialized
    refresh_model_inventory()


def test_frozen_restricted_safety_policies_are_unchanged():
    redgram = json.loads(
        (
            RUNTIME_ROOT
            / "redgram_mobilenetv3_small_v1_restricted"
            / "policy"
            / "RESTRICTED_RUNTIME_POLICY.json"
        ).read_text("utf-8")
    )
    chilli = json.loads(
        (
            RUNTIME_ROOT
            / "chilli_mobilenetv3_small_v1_restricted"
            / "policy"
            / "RESTRICTED_RUNTIME_POLICY.json"
        ).read_text("utf-8")
    )

    assert redgram["rules"]["redgram__leaf_spot"]["action"] == "ALWAYS_ABSTAIN"
    assert chilli["acceptance_rule"]["minimum_calibrated_confidence"] == 0.99
    assert chilli["acceptance_rule"]["minimum_calibrated_margin"] == 0.99
