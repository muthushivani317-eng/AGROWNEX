from pathlib import Path

from app.banana_v3.pytorch_runtime import PyTorchRuntime


def test_pytorch_runtime_is_lazy():
    runtime = PyTorchRuntime(Path("healthy.pt"), Path("disease.pt"))
    assert runtime.backend == "pytorch"
    assert runtime._models is None
