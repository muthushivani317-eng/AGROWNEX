import numpy as np
import io
from pathlib import Path

import pytest
from app.image_safety import assess_image_safety
from PIL import Image, ImageDraw, ImageFilter


def image(array: np.ndarray) -> Image.Image:
    return Image.fromarray(array.astype(np.uint8), "RGB")


def test_blank_uniform_and_extreme_images_fail_closed() -> None:
    for value in (0, 255, 80):
        result = assess_image_safety(Image.new("RGB", (224, 224), (value,) * 3))
        assert result.accepted is False


def test_noise_checkerboard_gradient_and_tiny_images_fail_closed() -> None:
    rng = np.random.default_rng(42)
    noise = image(rng.integers(0, 256, (224, 224, 3)))
    checker = np.indices((224, 224)).sum(axis=0) % 2 * 255
    checker_rgb = image(np.repeat(checker[:, :, None], 3, axis=2))
    gradient = np.linspace(30, 220, 224, dtype=np.uint8)
    gradient_rgb = image(np.repeat(np.tile(gradient, (224, 1))[:, :, None], 3, axis=2))
    tiny = Image.new("RGB", (32, 32), "green")
    for fixture in (noise, checker_rgb, gradient_rgb, tiny):
        assert assess_image_safety(fixture).accepted is False


def test_screenshot_like_image_fails_closed() -> None:
    screenshot = Image.new("RGB", (224, 224), "white")
    draw = ImageDraw.Draw(screenshot)
    for y in range(20, 200, 20):
        draw.rectangle((15, y, 175, y + 5), fill="black")
    assert assess_image_safety(screenshot).accepted is False


def test_natural_texture_is_not_blanket_rejected() -> None:
    rng = np.random.default_rng(7)
    base = rng.normal(105, 18, (224, 224, 3))
    textured = image(base).filter(ImageFilter.GaussianBlur(1.2))
    assert assess_image_safety(textured).accepted is True


@pytest.mark.parametrize("quality", [60, 90])
@pytest.mark.parametrize("size", [(387, 516), (224, 224), (774, 1032)])
def test_real_banana_leaf_texture_is_not_noise(quality, size) -> None:
    # User-supplied regression photo: checks upload quality only, not diagnosis.
    path = Path(__file__).parent / "fixtures/image_quality/banana_leaf_texture.jpg"
    with Image.open(path) as original:
        payload = io.BytesIO()
        original.resize(size).save(payload, format="JPEG", quality=quality)
        payload.seek(0)
        with Image.open(payload) as photo:
            assert assess_image_safety(photo, texture_policy="spatial").accepted is True


@pytest.mark.parametrize("block_size", [1, 2, 4, 8, 16, 32])
def test_checkerboards_remain_rejected(block_size) -> None:
    checker = (np.indices((224, 224)) // block_size).sum(axis=0) % 2 * 255
    assert not assess_image_safety(image(np.repeat(checker[:, :, None], 3, axis=2)), texture_policy="spatial").accepted


@pytest.mark.parametrize("seed", range(5))
def test_independent_noise_remains_rejected(seed) -> None:
    noise = np.random.default_rng(seed).integers(0, 256, (224, 224, 3))
    assert not assess_image_safety(image(noise), texture_policy="spatial").accepted


def test_controlled_routes_keep_existing_strict_policy() -> None:
    path = Path(__file__).parent / "fixtures/image_quality/banana_leaf_texture.jpg"
    with Image.open(path) as photo:
        assert assess_image_safety(photo).reason_code == "SYNTHETIC_OR_NOISE_PATTERN"


@pytest.mark.parametrize("value", [0, 255, 80])
def test_spatial_policy_still_rejects_blank_images(value) -> None:
    assert not assess_image_safety(
        Image.new("RGB", (224, 224), (value,) * 3), texture_policy="spatial"
    ).accepted
