"""Exact frozen preprocessing and hostile-image validation."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from .config import MAX_UPLOAD_BYTES, MEAN, MIN_IMAGE_SIDE, STD
from .error_codes import DecisionCode


class ImageValidationError(ValueError):
    """Safe image validation failure with a stable decision code."""

    def __init__(self, code: DecisionCode):
        super().__init__(code.value)
        self.code = code


def load_image(source: bytes | str | Path | Image.Image) -> Image.Image:
    try:
        if isinstance(source, bytes):
            if len(source) > MAX_UPLOAD_BYTES:
                raise ImageValidationError(DecisionCode.BV3_IMAGE_FORMAT_UNSUPPORTED)
            image = Image.open(BytesIO(source))
        elif isinstance(source, (str, Path)):
            image = Image.open(source)
        elif isinstance(source, Image.Image):
            image = source.copy()
        else:
            raise ImageValidationError(DecisionCode.BV3_IMAGE_UNREADABLE)
        image.load()
        image = ImageOps.exif_transpose(image)
    except ImageValidationError:
        raise
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise ImageValidationError(DecisionCode.BV3_IMAGE_UNREADABLE) from exc
    if image.width < MIN_IMAGE_SIDE or image.height < MIN_IMAGE_SIDE:
        raise ImageValidationError(DecisionCode.BV3_IMAGE_TOO_SMALL)
    if image.mode not in {"1", "L", "LA", "P", "RGB", "RGBA", "CMYK"}:
        raise ImageValidationError(DecisionCode.BV3_IMAGE_INVALID_CHANNELS)
    return image.convert("RGB")


def preprocess(source: bytes | str | Path | Image.Image) -> np.ndarray:
    """Return frozen float32 NCHW input with no augmentation."""
    image = load_image(source)
    width, height = image.size
    scale = 256 / min(width, height)
    image = image.resize((round(width * scale), round(height * scale)), Image.Resampling.BILINEAR)
    left = (image.width - 224) // 2
    top = (image.height - 224) // 2
    image = image.crop((left, top, left + 224, top + 224))
    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - np.asarray(MEAN, dtype=np.float32)) / np.asarray(STD, dtype=np.float32)
    return np.transpose(array, (2, 0, 1))[None, ...].astype(np.float32, copy=False)
