from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import torch
from PIL import Image

from app.crop_identity.artifacts import (
    CropIdentityArtifactError,
    EXPECTED_CHECKPOINT_SHA256,
    verify_bundle,
)
from app.crop_identity.pipeline import run_controlled_crop_identity_pipeline
from app.crop_identity.runtime import CropIdentityPrediction, CropIdentityRuntime

RUNTIME = (
    Path(__file__).resolve().parents[1]
    / "model_artifacts"
    / "frozen_runtime"
    / "crop_identity_v1"
)


def copied_runtime(tmp_path: Path) -> Path:
    destination = tmp_path / "runtime"
    shutil.copytree(RUNTIME, destination)
    return destination


def rewrite_json(path: Path, key: str, value):
    document = json.loads(path.read_text("utf-8"))
    document[key] = value
    path.write_text(json.dumps(document), encoding="utf-8")


def test_01_valid_bundle_loads():
    result = verify_bundle(RUNTIME, inspect_checkpoint=True)
    assert result["checkpoint_sha256"] == EXPECTED_CHECKPOINT_SHA256


def test_02_missing_checkpoint_fails(tmp_path):
    root = copied_runtime(tmp_path); (root / "best.pt").unlink()
    with pytest.raises(CropIdentityArtifactError, match="ARTIFACT_MISSING"):
        verify_bundle(root)


def test_03_wrong_checkpoint_hash_fails(tmp_path):
    root = copied_runtime(tmp_path)
    with (root / "best.pt").open("ab") as handle: handle.write(b"x")
    with pytest.raises(CropIdentityArtifactError, match="ARTIFACT_HASH_MISMATCH"):
        verify_bundle(root)


def test_04_wrong_model_name_fails(tmp_path):
    root = copied_runtime(tmp_path)
    rewrite_json(root / "runtime_config.json", "model_name", "wrong")
    with pytest.raises(CropIdentityArtifactError):
        verify_bundle(root)


def test_05_wrong_architecture_fails(tmp_path):
    root = copied_runtime(tmp_path)
    rewrite_json(root / "runtime_config.json", "architecture", "wrong")
    with pytest.raises(CropIdentityArtifactError):
        verify_bundle(root)


def test_06_wrong_class_order_fails(tmp_path):
    root = copied_runtime(tmp_path)
    rewrite_json(root / "runtime_config.json", "classes", ["paddy","banana","cotton","groundnut"])
    with pytest.raises(CropIdentityArtifactError):
        verify_bundle(root)


def test_07_wrong_preprocessing_fails(tmp_path):
    root = copied_runtime(tmp_path)
    rewrite_json(root / "preprocessing.json", "resize", 224)
    with pytest.raises(CropIdentityArtifactError):
        verify_bundle(root)


@pytest.mark.parametrize("name", ["temperature.json", "selected_class_specific_thresholds.json", "abstention_policy.json"])
def test_08_to_10_missing_policy_file_fails(tmp_path, name):
    root = copied_runtime(tmp_path); (root / name).unlink()
    with pytest.raises(CropIdentityArtifactError):
        verify_bundle(root)


def test_11_modified_packaged_artifact_detected(tmp_path):
    root = copied_runtime(tmp_path)
    with (root / "training_config.json").open("ab") as handle: handle.write(b" ")
    with pytest.raises(CropIdentityArtifactError, match="ARTIFACT_HASH_MISMATCH"):
        verify_bundle(root)


def test_12_runtime_stays_eval():
    runtime = CropIdentityRuntime(RUNTIME); runtime.load()
    assert runtime.ready and runtime._model.training is False


def test_13_probabilities_sum_to_one():
    prediction = CropIdentityRuntime(RUNTIME).predict(Image.new("RGB",(300,300),"green"))
    assert sum(prediction.calibrated_probabilities.values()) == pytest.approx(1.0)


def test_14_to_16_frozen_policy_is_reported():
    prediction = CropIdentityRuntime(RUNTIME).predict(Image.new("RGB",(300,300),"green"))
    assert prediction.applied_class_threshold == 0.5
    assert prediction.margin_threshold == 1.0
    assert prediction.entropy_threshold == pytest.approx(2.3740658328108566e-09)


def test_17_rejected_result_is_uncertain():
    prediction = CropIdentityRuntime(RUNTIME).predict(Image.new("RGB",(300,300),"green"))
    assert prediction.reason_code in {"CROP_MATCH", "CROP_IDENTITY_UNCERTAIN"}
    if not prediction.accepted:
        assert prediction.reason_code == "CROP_IDENTITY_UNCERTAIN"


def test_18_metadata_and_farmer_block():
    prediction = CropIdentityRuntime(RUNTIME).predict(Image.new("RGB",(300,300),"green"))
    assert prediction.model_name == "crop_identity_mobilenetv3_small_v1"
    assert prediction.checkpoint_sha256 == EXPECTED_CHECKPOINT_SHA256
    assert prediction.general_farmer_inference_authorized is False


def test_19_same_fixture_is_deterministic():
    runtime = CropIdentityRuntime(RUNTIME); image = Image.new("RGB",(300,300),"green")
    assert runtime.predict(image) == runtime.predict(image)


class FakeRuntime:
    def __init__(self, crop="banana", accepted=True, error=None):
        self.crop, self.accepted, self.error = crop, accepted, error
        self.calls = 0
    def predict(self, image):
        self.calls += 1
        if self.error: raise self.error
        return CropIdentityPrediction(
            "crop_identity_mobilenetv3_small_v1","v1",EXPECTED_CHECKPOINT_SHA256,
            self.crop,{self.crop:1.0},1.0,1.0,0.0,0.5,0.5,1.0,1e-9,
            self.accepted,"CROP_MATCH" if self.accepted else "CROP_IDENTITY_UNCERTAIN",
            "PUBLIC_DATASET_PROVISIONAL",False,False,
        )


def run(runtime, **kwargs):
    result=run_controlled_crop_identity_pipeline(
        authenticated=kwargs.get("authenticated",True),
        controlled_test_authorized=kwargs.get("authorized",True),
        image=kwargs.get("image",Image.new("RGB",(32,32))),
        quality_passed=kwargs.get("quality",True),
        plant_gate_passed=kwargs.get("plant",True), runtime=runtime,
    )
    return result


@pytest.mark.parametrize("crop", ["banana","paddy","cotton","groundnut"])
def test_20_to_23_crop_suggestion_never_dispatches_disease(crop):
    result=run(FakeRuntime(crop))
    assert result.reason_code=="CROP_MATCH"
    assert result.disease_adapter_called is False
    assert result.disease_adapter_name is None


def test_24_abstention_blocks(): assert run(FakeRuntime("banana",False)).reason_code=="CROP_IDENTITY_UNCERTAIN"
def test_25_runtime_unavailable_blocks(): assert run(FakeRuntime(error=CropIdentityArtifactError("MISSING"))).reason_code=="CROP_IDENTITY_RUNTIME_UNAVAILABLE"
def test_26_integrity_failure_blocks(): assert run(FakeRuntime(error=CropIdentityArtifactError("HASH_MISMATCH"))).reason_code=="CROP_IDENTITY_INTEGRITY_FAILURE"
def test_29_corrupt_blocks_all_models():
    runtime=FakeRuntime(); result=run(runtime,image=None); assert runtime.calls==0 and result.reason_code=="CORRUPT_OR_INVALID_IMAGE"
def test_28_low_quality_blocks():
    runtime=FakeRuntime(); result=run(runtime,quality=False); assert runtime.calls==0 and result.reason_code=="LOW_QUALITY_IMAGE"
def test_29_nonplant_blocks():
    runtime=FakeRuntime(); result=run(runtime,plant=False); assert runtime.calls==0 and result.reason_code=="NON_PLANT_REJECTED"
def test_30_invalid_auth_blocks():
    runtime=FakeRuntime(); result=run(runtime,authenticated=False); assert runtime.calls==0 and result.reason_code=="AUTHENTICATION_REQUIRED"
def test_31_general_farmer_blocked_without_controlled_role():
    runtime=FakeRuntime(); result=run(runtime,authorized=False); assert runtime.calls==0 and result.reason_code=="INFERENCE_NOT_AUTHORIZED"
