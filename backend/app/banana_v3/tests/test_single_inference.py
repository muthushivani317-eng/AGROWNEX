from io import BytesIO

import numpy as np
from PIL import Image

from app.banana_v3.inference_service import InferenceService


class FakeRuntime:
    backend = "pytorch"

    def healthy_logits(self, batch):
        return np.array([[0.0, 10.0]])

    def disease_logits(self, batch):
        return np.array([[0.0, 0.0, 10.0]])


def test_single_inference_returns_specific_accepted_class(tmp_path, monkeypatch):
    monkeypatch.setattr("app.banana_v3.inference_service.LOG_ROOT", tmp_path)
    service = InferenceService(tmp_path, runtime=FakeRuntime())
    stream = BytesIO()
    Image.new("RGB", (256, 256), "green").save(stream, "PNG")
    result = service.predict(stream.getvalue())
    assert result.result.class_id == "banana__sigatoka_leaf_spot"
    assert result.message_key == "banana.result.sigatoka"
