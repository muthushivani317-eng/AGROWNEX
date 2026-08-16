from pathlib import Path

from app.banana_v3.onnx_runtime import OnnxRuntime


def test_onnx_runtime_is_lazy():
    runtime = OnnxRuntime(Path("healthy.onnx"), Path("disease.onnx"))
    assert runtime.backend == "onnx"
    assert runtime._sessions is None
