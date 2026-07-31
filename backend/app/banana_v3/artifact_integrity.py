"""Fail-closed verification of the production artifact inventory."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class ArtifactIntegrityError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(root: Path) -> dict:
    path = root / "manifests" / "artifact_manifest.json"
    if not path.is_file():
        raise ArtifactIntegrityError("artifact manifest missing")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_artifacts(root: Path) -> dict:
    manifest = load_manifest(root)
    entries = manifest.get("artifacts", [])
    if not entries:
        raise ArtifactIntegrityError("artifact inventory empty")
    for entry in entries:
        path = root / entry["path"]
        if entry.get("required", True) and not path.is_file():
            raise ArtifactIntegrityError(f"required artifact missing: {entry['path']}")
        if path.is_file() and sha256_file(path) != entry["sha256"]:
            raise ArtifactIntegrityError(f"artifact hash mismatch: {entry['path']}")
    sums_path = root / "manifests" / "SHA256SUMS.txt"
    if not sums_path.is_file():
        raise ArtifactIntegrityError("SHA256SUMS.txt missing")
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        expected, relative = line.split(maxsplit=1)
        path = root / relative.strip()
        if not path.is_file() or sha256_file(path) != expected:
            raise ArtifactIntegrityError(f"checksum mismatch: {relative.strip()}")
    return manifest
