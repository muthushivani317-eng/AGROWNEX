import json
import shutil
from pathlib import Path

import pytest
from PIL import Image
from app.crop_identity_six_class_internal.runtime import (
    CLASSES,
    ROOT,
    IntegrityError,
    Runtime,
    verify,
)
from app.gemini_crop_identification.confirmation import ConfirmationStore


def test_installed_bundle_is_internal_only_and_verified():
    cfg = verify(ROOT)
    assert cfg["class_order"] == CLASSES
    assert cfg["general_farmer_release"] == "BLOCKED"
    assert cfg["farmer_confirmation_required"] is True


def test_tampered_model_fails_closed(tmp_path: Path):
    copy = tmp_path / "bundle"
    shutil.copytree(ROOT, copy)
    with (copy / "model.pt").open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(IntegrityError, match="ARTIFACT_INTEGRITY_FAILURE"):
        verify(copy)


def test_tampered_policy_fails_closed(tmp_path: Path):
    copy = tmp_path / "bundle"
    shutil.copytree(ROOT, copy)
    cfg = json.loads((copy / "runtime_config.json").read_text())
    cfg["general_farmer_release"] = "ALLOWED"
    (copy / "runtime_config.json").write_text(json.dumps(cfg))
    with pytest.raises(IntegrityError):
        verify(copy)


def test_health_redacts_paths_hashes_and_thresholds():
    response = Runtime(ROOT).health()
    text = json.dumps(response)
    assert response["status"] == "ready_internal_only"
    assert (
        "sha256" not in text.lower() and "threshold" not in text.lower() and str(ROOT) not in text
    )


def test_prediction_exposes_complete_calibrated_distribution_and_margin():
    result = Runtime(ROOT).predict(Image.new("RGB", (320, 240), "green"))
    probabilities = result["calibrated_probabilities"]
    assert set(probabilities) == set(CLASSES)
    assert sum(probabilities.values()) == pytest.approx(1.0, abs=1e-6)
    assert 0 <= result["margin"] <= 1


@pytest.mark.parametrize(
    "crop", ["banana", "paddy", "cotton", "groundnut", "chilli", "redgram"]
)
def test_unified_six_class_receipt_authorizes_crop_specific_validation(crop: str):
    store = ConfirmationStore()
    image = f"six-class-{crop}".encode()
    pending = store.create(actor_id="controlled-tester", image=image, identified_crop=crop)
    confirmed = store.confirm(
        actor_id="controlled-tester",
        request_id=pending.request_id,
        confirmed_crop=crop,
        correction=False,
    )
    validated = store.validate(
        actor_id="controlled-tester",
        token=str(confirmed.confirmation_token),
        crop=crop,
        image=image,
    )
    assert validated.confirmed_crop == crop
