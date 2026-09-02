import io

import pytest
from PIL import Image

from app.modules.disease.farmer_diagnosis_service import (
    DiseaseDiagnosisError,
    _decode_image,
)


@pytest.mark.parametrize(
    "size,color,reason",
    [((32, 32), "green", "IMAGE_TOO_SMALL"),
     ((128, 128), "black", "EXTREME_DARKNESS"),
     ((128, 128), "white", "EXTREME_BRIGHTNESS")],
)
def test_preserves_image_safety_reason(size, color, reason):
    payload = io.BytesIO()
    Image.new("RGB", size, color).save(payload, format="PNG")
    with pytest.raises(DiseaseDiagnosisError) as failure:
        _decode_image(payload.getvalue(), "image/png")
    assert failure.value.code == reason


def test_corrupt_image_stays_unusable():
    with pytest.raises(DiseaseDiagnosisError) as failure:
        _decode_image(b"not an image", "image/jpeg")
    assert failure.value.code == "IMAGE_UNUSABLE"
