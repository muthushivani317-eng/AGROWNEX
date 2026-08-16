import json
from pathlib import Path

from app.banana_v3.config import DISEASE_CLASSES, HEALTHY_CLASSES
from app.modules.disease.ml_runtime.constants import CLASS_TO_INDEX

ROOT = Path(__file__).resolve().parents[3]
REGISTRIES = ROOT / "recommendation_knowledge/runtime_labels"


def _labels(crop: str) -> list[str]:
    document = json.loads(
        (REGISTRIES / f"{crop}_runtime_labels.json").read_text(encoding="utf-8")
    )
    assert document["registry_status"] == "FROZEN"
    return [row["runtime_label_exact"] for row in document["labels"]]


def test_banana_registry_exactly_matches_runtime_class_order():
    assert _labels("banana") == [*HEALTHY_CLASSES, *DISEASE_CLASSES]


def test_legacy_crop_registries_exactly_match_runtime_mapping():
    ordered = list(CLASS_TO_INDEX)
    assert _labels("paddy") == [
        label for label in ordered if label.startswith(("paddy_", "rice_"))
    ]
    assert _labels("cotton") == [
        label for label in ordered if label.startswith("cotton_")
    ]
    assert _labels("groundnut") == [
        label for label in ordered if label.startswith("groundnut_")
    ]


def test_exact_spelling_capitalization_and_whitespace_are_preserved():
    assert "rice_blast" in _labels("paddy")
    assert "Rice_Blast" not in _labels("paddy")
    assert " rice_blast " not in _labels("paddy")
