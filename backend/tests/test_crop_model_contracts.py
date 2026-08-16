import pytest

from app.modules.disease.model_contracts import (
    DiagnosisAvailability,
    PENDING_PROVIDERS,
)


@pytest.mark.parametrize("crop", ["chilli", "redgram"])
def test_pending_adapter_returns_typed_unavailable_without_diagnosis(crop: str) -> None:
    result = PENDING_PROVIDERS[crop].predict(b"not-inspected")
    assert result.status is DiagnosisAvailability.MODEL_NOT_AVAILABLE
    assert result.crop_id == crop
    assert result.diagnostic_result is None
