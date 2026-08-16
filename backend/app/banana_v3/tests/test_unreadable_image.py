from app.banana_v3.error_codes import DecisionCode
from app.banana_v3.inference_service import InferenceService


class FakeRuntime:
    backend = "pytorch"


def test_unreadable_image_is_safe_error(tmp_path):
    result = InferenceService(tmp_path, runtime=FakeRuntime()).predict(b"not-an-image")
    assert result.decision_code == DecisionCode.BV3_IMAGE_UNREADABLE
    assert result.message_key == "banana.error.unreadable_image"
