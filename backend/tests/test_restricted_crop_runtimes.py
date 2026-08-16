from __future__ import annotations

import json
import shutil
from dataclasses import dataclass

import pytest
from app.restricted_crops import integrity
from app.restricted_crops.api_router import normalized_response
from app.restricted_crops.integrity import (
    PACKAGES,
    RestrictedRuntimeIntegrityError,
    verify_restricted_package,
)
from app.restricted_crops.runtime import get_restricted_runtime


@dataclass
class Result:
    status: str
    predicted_class: str | None
    calibrated_confidence: float | None
    calibrated_margin: float | None
    abstention_code: str | None = None


@pytest.mark.parametrize("crop_id", ["redgram", "chilli"])
def test_exact_restricted_package_and_checkpoint_load(crop_id):
    assert verify_restricted_package(crop_id).is_dir()
    runtime = get_restricted_runtime(crop_id).load()
    assert runtime.class_to_index == PACKAGES[crop_id]["classes"]


def test_redgram_leaf_spot_always_abstains_at_confidence_one():
    response = normalized_response(
        "redgram",
        Result(
            "ACCEPTED_RESTRICTED_RESULT",
            "redgram__leaf_spot",
            1.0,
            1.0,
        ),
    )
    assert response["status"] == "abstained"
    assert response["recommendation_available"] is False


@pytest.mark.parametrize(
    ("confidence", "margin", "accepted"),
    [(0.989999, 1.0, False), (1.0, 0.989999, False), (0.99, 0.99, True)],
)
def test_chilli_frozen_boundary_contract(confidence, margin, accepted):
    assert ((confidence >= 0.99) and (margin >= 0.99)) is accepted


@pytest.mark.parametrize("label", list(PACKAGES["chilli"]["classes"]))
def test_all_exact_chilli_labels_are_preserved(label):
    response = normalized_response(
        "chilli",
        Result("ACCEPTED_RESTRICTED_RESULT", label, 1.0, 1.0),
    )
    assert response["status"] == "accepted"
    assert response["predicted_label"] == label


def test_unknown_label_fails_closed():
    response = normalized_response(
        "chilli",
        Result("ACCEPTED_RESTRICTED_RESULT", "chilli__cercospora", 1.0, 1.0),
    )
    assert response["status"] == "runtime_error"
    assert response["predicted_label"] is None


def test_modified_package_file_fails_integrity(tmp_path, monkeypatch):
    source = verify_restricted_package("chilli")
    destination = tmp_path / source.name
    shutil.copytree(source, destination)
    config_path = destination / "config" / "runtime_config.json"
    config = json.loads(config_path.read_text("utf-8"))
    config["temperature"] = 0.5
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(integrity, "RUNTIME_ROOT", tmp_path)
    with pytest.raises(RestrictedRuntimeIntegrityError, match="PACKAGE_HASH_MISMATCH"):
        integrity.verify_restricted_package("chilli")
