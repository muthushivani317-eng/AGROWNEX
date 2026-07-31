"""Read-only model-lineage access."""
from __future__ import annotations

import json
from pathlib import Path

from .config import ARTIFACT_ROOT


def get_model_lineage(root: Path = ARTIFACT_ROOT) -> dict:
    return json.loads((root / "runtime" / "model_lineage.json").read_text(encoding="utf-8"))
