"""Lazy adapter that refuses missing or unapproved Green Gram artifacts."""

from __future__ import annotations

import importlib.util
import sys
import threading
from pathlib import Path
from typing import Any

from PIL import Image

from app.core.config import settings


class GreenGramModelUnavailableError(RuntimeError):
    pass


class GreenGramPredictionService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pipeline: Any | None = None

    def load(self) -> None:
        with self._lock:
            if self._pipeline is not None:
                return
            module_path = Path(settings.green_gram_inference_module_path)
            if not module_path.is_file():
                raise GreenGramModelUnavailableError("GREEN_GRAM_INFERENCE_MODULE_MISSING")
            spec = importlib.util.spec_from_file_location("agronex_green_gram_inference_runtime", module_path)
            if spec is None or spec.loader is None:
                raise GreenGramModelUnavailableError("GREEN_GRAM_INFERENCE_MODULE_INVALID")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            try:
                spec.loader.exec_module(module)
                pipeline = module.GreenGramExploratoryInferencePipeline(
                    Path(settings.green_gram_model_release_dir), settings.green_gram_inference_device
                )
                pipeline.load()
            except Exception as exc:
                sys.modules.pop(spec.name, None)
                raise GreenGramModelUnavailableError("GREEN_GRAM_MODEL_UNAVAILABLE") from exc
            self._pipeline = pipeline

    def predict(self, image: Image.Image) -> dict[str, Any]:
        self.load()
        assert self._pipeline is not None
        return self._pipeline.predict(image)


_service = GreenGramPredictionService()


def get_green_gram_prediction_service() -> GreenGramPredictionService:
    return _service
