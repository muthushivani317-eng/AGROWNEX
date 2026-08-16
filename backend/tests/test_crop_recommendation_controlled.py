from __future__ import annotations

import math

import pytest
from app.modules.crop_recommendation.runtime import CropRecommendationRuntime
from app.modules.crop_recommendation.schemas import CropRecommendationRequest
from pydantic import ValidationError


def sample(**changes: float) -> CropRecommendationRequest:
    values = {
        "nitrogen": 90,
        "phosphorus": 42,
        "potassium": 43,
        "temperature_c": 20.9,
        "humidity_percent": 82,
        "ph": 6.5,
        "rainfall_mm": 203,
    }
    values.update(changes)
    return CropRecommendationRequest(**values)


def test_sealed_runtime_returns_ranked_finite_outputs():
    result, alternatives = CropRecommendationRuntime().predict(sample())
    assert result.crop == "rice"
    assert math.isfinite(result.model_probability)
    assert 0 <= result.model_probability <= 1
    assert len(alternatives) == 2
    assert result.model_probability >= alternatives[0].model_probability


@pytest.mark.parametrize(
    ("field", "value"),
    [("ph", 15), ("humidity_percent", 101), ("nitrogen", -1), ("rainfall_mm", 2001)],
)
def test_out_of_contract_measurements_are_rejected(field: str, value: float):
    with pytest.raises(ValidationError):
        sample(**{field: value})


def test_artifact_is_explicitly_controlled_and_unvalidated():
    metadata = CropRecommendationRuntime().metadata
    assert metadata["general_farmer_release_authorized"] is False
    assert metadata["validation_status"] == "NO_INDEPENDENT_AGROWAI_EVALUATION"
    assert metadata["artifact_status"] == "PROVISIONAL_CONTROLLED_TEST_ONLY"
