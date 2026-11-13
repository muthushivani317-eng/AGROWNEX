"""Lazy, per-worker adapter for the approved Groundnut inference pipeline."""

from __future__ import annotations

import importlib.util
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

from app.core.config import settings


class GroundnutModelUnavailableError(RuntimeError):
    """The approved model or its inference runtime cannot be loaded."""


class GroundnutPredictionService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pipeline: Any | None = None
        self._module: ModuleType | None = None

    @staticmethod
    def _load_module(path: Path) -> ModuleType:
        if not path.is_file():
            raise GroundnutModelUnavailableError("GROUNDNUT_INFERENCE_MODULE_MISSING")
        module_name = "agronex_groundnut_inference_runtime"
        existing = sys.modules.get(module_name)
        if existing is not None:
            return existing
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise GroundnutModelUnavailableError("GROUNDNUT_INFERENCE_MODULE_INVALID")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            sys.modules.pop(module_name, None)
            raise GroundnutModelUnavailableError("GROUNDNUT_INFERENCE_MODULE_LOAD_FAILED") from exc
        return module

    def load(self) -> None:
        with self._lock:
            if self._pipeline is not None:
                return
            try:
                module = self._load_module(Path(settings.groundnut_inference_module_path))
                pipeline_class = module.GroundnutInferencePipeline
                requested_device = settings.groundnut_inference_device
                try:
                    pipeline = pipeline_class(
                        release_dir=Path(settings.groundnut_model_release_dir),
                        device=requested_device,
                    )
                    pipeline.load()
                except RuntimeError as exc:
                    if requested_device == "cuda" and settings.groundnut_allow_cpu_fallback and str(exc) == "CUDA_REQUESTED_BUT_UNAVAILABLE":
                        pipeline = pipeline_class(
                            release_dir=Path(settings.groundnut_model_release_dir),
                            device="cpu",
                        )
                        pipeline.load()
                    else:
                        raise
            except GroundnutModelUnavailableError:
                raise
            except Exception as exc:
                raise GroundnutModelUnavailableError("GROUNDNUT_MODEL_LOAD_FAILED") from exc
            self._module = module
            self._pipeline = pipeline

    def predict(self, image: Image.Image) -> dict[str, Any]:
        self.load()
        assert self._pipeline is not None
        try:
            return self._pipeline.predict(image).to_dict()
        except Exception as exc:
            raise GroundnutModelUnavailableError("GROUNDNUT_INFERENCE_FAILED") from exc


_service = GroundnutPredictionService()


def get_groundnut_prediction_service() -> GroundnutPredictionService:
    return _service
