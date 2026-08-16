import numpy as np
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
