"""Production artifact load and deterministic image smoke test."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.banana_v3.inference_service import InferenceService


def main() -> None:
    service = InferenceService()
    service.load()
    result = service.predict(Image.new("RGB", (256, 256), "green"))
    if result.status == "error":
        raise SystemExit(f"smoke test failed: {result.decision_code}")
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
