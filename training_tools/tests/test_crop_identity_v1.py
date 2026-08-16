from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from training_tools.crop_identity_v1.abstention import decide
from training_tools.crop_identity_v1.calibration import (
    calibrated_probabilities,
    fit_temperature,
)
from training_tools.crop_identity_v1.common import CLASSES, ManifestDataset, class_weights
from training_tools.crop_identity_v1.package_runtime import REQUIRED, package


def test_class_order_is_frozen():
    assert CLASSES == ("banana", "paddy", "cotton", "groundnut")


def test_class_weights_downweight_majority():
    dataset = object.__new__(ManifestDataset)
    dataset.rows = (
        [{"crop_class": "banana"}] * 2
        + [{"crop_class": "paddy"}] * 8
        + [{"crop_class": "cotton"}] * 2
        + [{"crop_class": "groundnut"}] * 2
    )
    weights = class_weights(dataset)
    assert weights[1] < weights[0]


def test_temperature_improves_or_preserves_nll_and_probabilities_sum_to_one():
    logits = torch.tensor([[6.0, 0.0], [6.0, 0.0], [0.0, 6.0], [6.0, 0.0]])
    labels = torch.tensor([0, 1, 1, 0])
    temperature, before, after = fit_temperature(logits, labels)
    assert temperature > 0
    assert after <= before + 1e-9
    probabilities = calibrated_probabilities(logits, temperature)
    assert torch.allclose(probabilities.sum(dim=1), torch.ones(4))


def test_abstention_fails_closed():
    result = decide(
        [0.4, 0.3, 0.2, 0.1],
        list(CLASSES),
        {},
        fallback_threshold=0.8,
        margin_threshold=0.2,
        entropy_threshold=1.0,
    )
    assert result["accepted"] is False
    assert result["reason_code"] == "CROP_IDENTITY_UNCERTAIN"


def test_packaging_requires_complete_evidence(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(RuntimeError, match="RUNTIME_PACKAGE_INCOMPLETE"):
        package(source, tmp_path / "runtime")


def test_package_hashes_complete_bundle(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    for name in REQUIRED:
        (source / name).write_bytes(b"checkpoint" if name.endswith(".pt") else b"{}")
    destination = tmp_path / "runtime"
    hashes = package(source, destination)
    assert (destination / "SHA256SUMS.txt").is_file()
    assert (destination / "DEPLOYMENT_BUNDLE_SHA256SUMS.txt").is_file()
    runtime = json.loads((destination / "runtime_config.json").read_text())
    assert runtime["general_farmer_inference_authorized"] is False
    assert hashes
