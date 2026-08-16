"""Fail-closed production bundle builder."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.banana_v3.artifact_integrity import sha256_file, verify_artifacts
from app.banana_v3.config import BUNDLE_VERSION, EXPECTED_CHECKPOINT_HASHES


def main() -> None:
    backend = Path(__file__).resolve().parents[1]
    package = backend / "app/banana_v3"
    artifacts = package / "artifacts"
    for relative, expected in EXPECTED_CHECKPOINT_HASHES.items():
        path = artifacts / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise SystemExit(f"missing or mismatched frozen checkpoint: {path}")
    for relative in ("onnx/healthy_gate.onnx", "onnx/disease_classifier.onnx"):
        if not (artifacts / relative).is_file():
            raise SystemExit(f"missing verified ONNX artifact: {artifacts / relative}")
    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "app/banana_v3/tests", "-q"],
        cwd=backend,
        check=False,
    )
    if tests.returncode:
        raise SystemExit("unit tests failed")
    inventory = []
    for path in sorted((p for p in artifacts.rglob("*") if p.is_file())):
        if path.name in {"artifact_manifest.json", "SHA256SUMS.txt"}:
            continue
        inventory.append({
            "path": path.relative_to(artifacts).as_posix(),
            "sha256": sha256_file(path),
            "required": True,
        })
    manifest = {
        "bundle_version": BUNDLE_VERSION,
        "created_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "VERIFIED",
        "artifacts": inventory,
        "source_checkpoint_hashes": {
            key: value for key, value in EXPECTED_CHECKPOINT_HASHES.items()
        },
        "onnx_hashes": {
            "healthy_gate": sha256_file(artifacts / "onnx/healthy_gate.onnx"),
            "disease_classifier": sha256_file(artifacts / "onnx/disease_classifier.onnx"),
        },
    }
    manifest_path = artifacts / "manifests/artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    files = [p for p in artifacts.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"]
    (artifacts / "manifests/SHA256SUMS.txt").write_text(
        "".join(
            f"{sha256_file(path)}  {path.relative_to(artifacts).as_posix()}\n"
            for path in sorted(files)
        )
    )
    verify_artifacts(artifacts)
    smoke = subprocess.run(
        [sys.executable, "scripts/smoke_test_banana_v3.py"], cwd=backend, check=False
    )
    if smoke.returncode:
        raise SystemExit("smoke test failed")
    output = backend / "banana_v3_production_bundle.zip"
    include = [package, backend / "scripts", backend / "deployment/banana_v3"]
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for base in include:
            for path in base.rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts:
                    archive.write(path, path.relative_to(backend))
    with tempfile.TemporaryDirectory(prefix="banana-v3-build-") as directory:
        subprocess.run(
            [sys.executable, "scripts/verify_banana_v3_bundle.py", str(output)],
            cwd=backend,
            check=True,
        )
    receipt = {
        "bundle_version": BUNDLE_VERSION,
        "bundle_path": str(output),
        "bundle_sha256": sha256_file(output),
        "created_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tests_passed": True,
        "smoke_test_passed": True,
        "integrity_verified": True,
    }
    (backend / "banana_v3_build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
