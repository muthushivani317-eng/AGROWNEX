"""Fail-closed verification of the four frozen model artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .constants import CLASS_TO_INDEX, EXPECTED_HASHES


class ArtifactVerificationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifacts(directory: Path) -> dict[str, str]:
    verified: dict[str, str] = {}
    for name, expected in EXPECTED_HASHES.items():
        path = directory / name
        if not path.is_file():
            raise ArtifactVerificationError(f"required frozen artifact missing: {name}")
        actual = sha256_file(path)
        if actual != expected:
            raise ArtifactVerificationError(f"frozen artifact hash mismatch: {name}")
        verified[name] = actual
    try:
        mapping = json.loads((directory / "class_to_index.json").read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactVerificationError("class mapping is unreadable") from exc
    if mapping != CLASS_TO_INDEX or sorted(mapping.values()) != list(range(9)):
        raise ArtifactVerificationError("class mapping differs from the frozen nine-class mapping")
    return verified
