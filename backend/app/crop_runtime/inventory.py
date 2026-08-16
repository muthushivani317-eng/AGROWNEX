"""Sanitized, executable inventory for the controlled disease workflow."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from importlib import import_module
from pathlib import Path

from app.crop_id_safety.gates import verify_safety_artifact
from app.crop_identity_six_class_internal.runtime import Runtime as CropIdentityRuntime

from .readiness import ReadinessResolver
from .registry import load_registry

REQUIRED_INFERENCE_PACKAGES = (
    "numpy",
    "onnx",
    "onnxruntime",
    "PIL",
    "torch",
    "torchvision",
)
PILOT_CROPS = ("banana", "paddy", "cotton", "groundnut", "redgram", "chilli")


@dataclass(frozen=True)
class ModelInventory:
    dependencies: dict[str, bool]
    crop_identity_ready: bool
    safety_gate_ready: bool
    disease_runtimes: dict[str, bool]
    runtime_diagnostics: dict[str, str]

    def public_dict(self) -> dict[str, object]:
        return asdict(self)


def dependency_inventory() -> dict[str, bool]:
    result: dict[str, bool] = {}
    for package in REQUIRED_INFERENCE_PACKAGES:
        try:
            import_module(package)
            result[package] = True
        except (ImportError, OSError):
            result[package] = False
    return result


def inventory_ready(inventory) -> bool:
    return bool(
        inventory.dependencies
        and all(inventory.dependencies.values())
        and inventory.crop_identity_ready
        and inventory.safety_gate_ready
        and inventory.disease_runtimes
        and all(inventory.disease_runtimes.values())
    )


def build_model_inventory(project_root: Path) -> ModelInventory:
    registry = load_registry()
    resolver = ReadinessResolver(registry, project_root)
    disease_runtimes: dict[str, bool] = {}
    diagnostics: dict[str, str] = {}
    for crop_id in PILOT_CROPS:
        try:
            result = resolver.resolve(crop_id)
            disease_runtimes[crop_id] = result.runtime_loadable
            diagnostics[crop_id] = result.readiness_reason
        except Exception:
            disease_runtimes[crop_id] = False
            diagnostics[crop_id] = "load_failed"

    try:
        CropIdentityRuntime().load()
        crop_identity_ready = True
    except Exception:
        crop_identity_ready = False
    try:
        verify_safety_artifact()
        safety_gate_ready = True
    except Exception:
        safety_gate_ready = False

    return ModelInventory(
        dependencies=dependency_inventory(),
        crop_identity_ready=crop_identity_ready,
        safety_gate_ready=safety_gate_ready,
        disease_runtimes=disease_runtimes,
        runtime_diagnostics=diagnostics,
    )


@lru_cache(maxsize=1)
def get_model_inventory() -> ModelInventory:
    return build_model_inventory(Path(__file__).resolve().parents[2])


def refresh_model_inventory() -> None:
    get_model_inventory.cache_clear()
