from __future__ import annotations

import importlib.util
import sys
import threading
from typing import Any

from .integrity import verify_restricted_package

RUNTIME_CLASSES = {
    "redgram": "RestrictedRedgramRuntime",
    "chilli": "RestrictedChilliRuntime",
}


class RestrictedRuntimeManager:
    def __init__(self, crop_id: str) -> None:
        if crop_id not in RUNTIME_CLASSES:
            raise ValueError("UNSUPPORTED_CROP")
        self.crop_id = crop_id
        self._runtime: Any = None
        self._lock = threading.RLock()

    @property
    def ready(self) -> bool:
        return self._runtime is not None

    def load(self) -> Any:
        with self._lock:
            if self._runtime is not None:
                return self._runtime
            root = verify_restricted_package(self.crop_id)
            module_path = root / "runtime" / "restricted_runtime.py"
            module_name = f"agrowai_restricted_{self.crop_id}"
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise RuntimeError("RUNTIME_MODULE_UNAVAILABLE")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            runtime_class = getattr(module, RUNTIME_CLASSES[self.crop_id])
            self._runtime = runtime_class(root, device="cpu")
            return self._runtime

    def predict(self, image):
        return self.load().predict(image)


_RUNTIMES = {
    crop_id: RestrictedRuntimeManager(crop_id)
    for crop_id in RUNTIME_CLASSES
}


def get_restricted_runtime(crop_id: str) -> RestrictedRuntimeManager:
    try:
        return _RUNTIMES[crop_id]
    except KeyError as exc:
        raise ValueError("UNSUPPORTED_CROP") from exc
