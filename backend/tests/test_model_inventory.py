from __future__ import annotations

from types import SimpleNamespace

from app.crop_runtime.inventory import dependency_inventory, inventory_ready


def test_dependency_inventory_reports_each_required_inference_package(monkeypatch) -> None:
    def import_module(name: str):
        if name == "onnx":
            raise ModuleNotFoundError(name)
        return object()

    monkeypatch.setattr("app.crop_runtime.inventory.import_module", import_module)

    assert dependency_inventory() == {
        "numpy": True,
        "onnx": False,
        "onnxruntime": True,
        "PIL": True,
        "torch": True,
        "torchvision": True,
    }


def test_inventory_requires_dependencies_crop_identity_safety_and_all_crops() -> None:
    complete = SimpleNamespace(
        dependencies={"torch": True},
        crop_identity_ready=True,
        safety_gate_ready=True,
        disease_runtimes={"banana": True, "paddy": True},
    )
    assert inventory_ready(complete) is True
    assert not inventory_ready(
        SimpleNamespace(**{**complete.__dict__, "crop_identity_ready": False})
    )
    assert not inventory_ready(
        SimpleNamespace(**{**complete.__dict__, "safety_gate_ready": False})
    )
    assert not inventory_ready(
        SimpleNamespace(**{**complete.__dict__, "dependencies": {"torch": False}})
    )
    assert not inventory_ready(
        SimpleNamespace(
            **{**complete.__dict__, "disease_runtimes": {"banana": False}}
        )
    )
