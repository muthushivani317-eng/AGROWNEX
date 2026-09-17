from io import BytesIO

import numpy as np
from app.banana_v3.preprocessing import preprocess
from PIL import Image


def test_preprocessing_is_nchw_float32():
    stream = BytesIO()
    Image.new("RGB", (300, 260), "green").save(stream, "PNG")
    result = preprocess(stream.getvalue())
    assert result.shape == (1, 3, 224, 224)
    assert result.dtype == np.float32
