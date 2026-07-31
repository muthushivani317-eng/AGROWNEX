"""Hostile-input-safe image decoding and frozen evaluation preprocessing."""

from __future__ import annotations

import base64
import binascii
import io
import warnings
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

from .errors import InvalidDiseaseImageError

ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
FORMAT_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


@dataclass(frozen=True)
class DecodedImage:
    image: Image.Image
    byte_count: int


def decode_image(value: str, mime_type: str) -> DecodedImage:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise InvalidDiseaseImageError("Only JPEG, PNG, and WebP images are accepted.")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidDiseaseImageError("Invalid base64 image data.") from exc
    if not raw or len(raw) > settings.disease_max_image_bytes:
        raise InvalidDiseaseImageError("Image is empty or exceeds the size limit.")
    old_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = settings.disease_max_image_pixels
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                source.verify()
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in FORMAT_TO_MIME:
                    raise InvalidDiseaseImageError("Decoded image format is unsupported.")
                if FORMAT_TO_MIME[source.format] != mime_type:
                    raise InvalidDiseaseImageError("Declared MIME type does not match image data.")
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.load()
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise InvalidDiseaseImageError("Image is corrupt or unsafe to decode.") from exc
    finally:
        Image.MAX_IMAGE_PIXELS = old_limit
    if image.width < 1 or image.height < 1:
        raise InvalidDiseaseImageError("Image dimensions are empty.")
    return DecodedImage(image=image, byte_count=len(raw))
