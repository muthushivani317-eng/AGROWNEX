"""Frozen MobileNetV3 disease-classifier runtime."""

from .runtime import FrozenModelRuntime, get_model_runtime

__all__ = ["FrozenModelRuntime", "get_model_runtime"]
