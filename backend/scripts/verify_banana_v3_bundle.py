"""Verify a Banana V3 directory or ZIP in an isolated temporary directory."""
from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.banana_v3.artifact_integrity import verify_artifacts


def safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as source:
        root = destination.resolve()
        for member in source.infolist():
            target = (destination / member.filename).resolve()
            if root not in target.parents and target != root:
                raise RuntimeError(f"unsafe ZIP member: {member.filename}")
        source.extractall(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    if args.bundle.is_dir():
        verify_artifacts(args.bundle / "app/banana_v3/artifacts")
        return
    with tempfile.TemporaryDirectory(prefix="banana-v3-verify-") as directory:
        root = Path(directory)
        safe_extract(args.bundle, root)
        verify_artifacts(root / "app/banana_v3/artifacts")


if __name__ == "__main__":
    main()
