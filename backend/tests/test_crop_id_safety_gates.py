import json
import shutil
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
from app.crop_id_safety.gates import (
    ARTIFACT_ROOT,
    SafetyArtifactError,
    assess_ambiguity,
    assess_ood,
    assess_plant,
    assess_quality,
    verify_safety_artifact,
)
from PIL import Image, ImageDraw, ImageFilter


def leaf_like() -> Image.Image:
    image = Image.new("RGB", (224, 224), (120, 90, 55))
    draw = ImageDraw.Draw(image)
    draw.ellipse((30, 15, 195, 210), fill=(25, 155, 45))
    draw.line((112, 20, 112, 205), fill=(220, 230, 120), width=4)
    return image


def test_safety_artifact_integrity_and_policy() -> None:
    config = verify_safety_artifact()
    assert config["scope"] == "INTERNAL_ONLY"
    assert config["general_farmer_release"] == "BLOCKED"


def test_safety_artifact_tamper_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "artifact"
    shutil.copytree(ARTIFACT_ROOT, root)
    config = json.loads((root / "safety_config.json").read_text())
    config["general_farmer_release"] = "ALLOWED"
    (root / "safety_config.json").write_text(json.dumps(config))
    with pytest.raises(SafetyArtifactError):
        verify_safety_artifact(root)


@pytest.mark.parametrize(
    "image",
    [
        Image.new("RGB", (224, 224), "black"),
        Image.new("RGB", (224, 224), "white"),
        Image.new("RGB", (16, 16), "green"),
        Image.fromarray(np.random.default_rng(7).integers(0, 256, (224, 224, 3), dtype=np.uint8)),
        leaf_like().filter(ImageFilter.GaussianBlur(40)),
    ],
)
def test_low_quality_images_are_rejected(image: Image.Image) -> None:
    assert assess_quality(image, verify_safety_artifact()).outcome == "LOW_QUALITY"


def test_obvious_non_plant_is_not_passed_as_plant() -> None:
    image = Image.new("RGB", (224, 224), (160, 80, 40))
    result = assess_plant(image, verify_safety_artifact())
    assert result["outcome"] == "NON_PLANT"


def test_plant_like_fixture_remains_ood_uncertain_without_independent_reference() -> None:
    config = verify_safety_artifact()
    plant = assess_plant(leaf_like(), config)
    assert plant["outcome"] == "PLANT"
    assert assess_ood(plant, config)["outcome"] == "OOD_UNCERTAIN"


def test_ambiguity_requires_transform_stability() -> None:
    runtime = Mock()
    runtime.predict.side_effect = [
        {"status": "identified", "identified_crop": "banana"},
        {"status": "identified", "identified_crop": "chilli"},
        {"status": "identified", "identified_crop": "banana"},
    ]
    assert assess_ambiguity(runtime, leaf_like())["outcome"] == "AMBIGUOUS_IMAGE"


def test_supported_stable_candidate_requires_confirmation() -> None:
    runtime = Mock()
    runtime.predict.return_value = {
        "status": "identified",
        "identified_crop": "banana",
        "farmer_confirmation_required": True,
    }
    result = assess_ambiguity(runtime, leaf_like())
    assert result["outcome"] == "IDENTITY_ACCEPTABLE_FOR_CONFIRMATION"
    assert all(item["farmer_confirmation_required"] for item in result["runtime_results"])
