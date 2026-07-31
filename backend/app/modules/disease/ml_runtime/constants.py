"""Immutable Phase 3 Part 3 runtime identity and decision settings."""

MODEL_NAME = "mobilenetv3_small"
MODEL_VERSION = "mobilenetv3_small_v1"
IMAGE_SIZE = 224
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
TEMPERATURE = 1.1593322394366143
CONFIDENCE_THRESHOLD = 0.80
MARGIN_THRESHOLD = 0.00

EXPECTED_HASHES = {
    "best.pt": "f9719d48d3a8d274d039f0bd36d78cc5fa1282a8f15b2f471ab27d5c043e8117",
    "class_to_index.json": "639d3615eb166f860221a2290ba87dabcca814ba74723315422e5a567388cc29",
    "v1_split_manifest.json": "482cf5f9144cc0563e4e85d2bb3a9cb0e901896edf6bcae2d949dadfa65c232f",
    "runtime_training_config_snapshot.json": (
        "018769fba169cbe3421d8d6adb9b4fb0af89f1029f2e37460c08cf2cec08ee46"
    ),
}
CLASS_TO_INDEX = {
    "cotton_fusarium_wilt": 0,
    "cotton_healthy": 1,
    "cotton_verticillium_wilt": 2,
    "groundnut_healthy": 3,
    "groundnut_rust": 4,
    "paddy_healthy": 5,
    "rice_blast": 6,
    "rice_brown_leaf_spot": 7,
    "rice_tungro": 8,
}
INDEX_TO_CLASS = {value: key for key, value in CLASS_TO_INDEX.items()}
CLASS_TO_CROP = {
    name: ("rice" if name.startswith(("rice_", "paddy_")) else name.split("_", 1)[0])
    for name in CLASS_TO_INDEX
}
SUPPORTED_CROPS = ("rice", "cotton", "groundnut")
HEALTHY_CLASSES = frozenset({"cotton_healthy", "groundnut_healthy", "paddy_healthy"})
