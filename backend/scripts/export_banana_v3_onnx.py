"""Export the two frozen checkpoints to ONNX opset 17 and verify parity."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.banana_v3.artifact_integrity import sha256_file
from app.banana_v3.pytorch_runtime import PyTorchRuntime

TOLERANCE = 1e-4


def export_one(checkpoint: Path, destination: Path, classes: int) -> dict:
    import onnx
    import onnxruntime as ort
    import torch

    model = PyTorchRuntime._load(checkpoint, classes)
    sample = torch.zeros((2, 3, 224, 224), dtype=torch.float32)
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        sample,
        destination,
        input_names=["image"],
        output_names=["logits"],
        dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
    )
    onnx.checker.check_model(onnx.load(destination))
    with torch.inference_mode():
        expected = model(sample).numpy()
    session = ort.InferenceSession(str(destination), providers=["CPUExecutionProvider"])
    actual = session.run(["logits"], {"image": sample.numpy()})[0]
    difference = float(np.max(np.abs(expected - actual)))
    if difference > TOLERANCE:
        raise RuntimeError(f"ONNX parity failed: {difference} > {TOLERANCE}")
    return {"sha256": sha256_file(destination), "max_absolute_difference": difference}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=Path("app/banana_v3/artifacts"))
    args = parser.parse_args()
    root = args.artifact_root
    results = {
        "healthy_gate": export_one(
            root / "checkpoints/healthy_gate_best.pt", root / "onnx/healthy_gate.onnx", 2
        ),
        "disease_classifier": export_one(
            root / "checkpoints/disease_classifier_best.pt",
            root / "onnx/disease_classifier.onnx",
            3,
        ),
        "opset": 17,
        "tolerance": TOLERANCE,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    (root / "onnx/export_receipt.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
