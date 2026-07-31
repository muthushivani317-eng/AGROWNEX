from __future__ import annotations

import hashlib
import json
from pathlib import Path

RUNTIME_ROOT = (
    Path(__file__).resolve().parents[2] / "model_artifacts" / "frozen_runtime"
)

PACKAGES = {
    "redgram": {
        "folder": "redgram_mobilenetv3_small_v1_restricted",
        "runtime_id": "redgram_mobilenetv3_small_v1_restricted",
        "checkpoint_sha256": (
            "5b95e1658f6bb0d83a3cef8b455533599482d102b86a326f184477f214269e72"
        ),
        "classes": {
            "redgram__healthy": 0,
            "redgram__leaf_spot": 1,
            "redgram__sterility_mosaic": 2,
        },
    },
    "chilli": {
        "folder": "chilli_mobilenetv3_small_v1_restricted",
        "runtime_id": "chilli_mobilenetv3_small_v1_restricted",
        "checkpoint_sha256": (
            "adab7c3eefa009b78e1c9d335fc088d74b5f2b456eb7196950da385ed761ec26"
        ),
        "classes": {
            "chilli__bacterial_spot": 0,
            "chilli__cercospora_leaf_spot": 1,
            "chilli__healthy": 2,
            "chilli__leaf_curl_virus": 3,
        },
    },
}


class RestrictedRuntimeIntegrityError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_restricted_package(crop_id: str) -> Path:
    contract = PACKAGES.get(crop_id)
    if contract is None:
        raise RestrictedRuntimeIntegrityError("UNSUPPORTED_CROP")
    root = (RUNTIME_ROOT / str(contract["folder"])).resolve()
    if RUNTIME_ROOT.resolve() not in root.parents or not root.is_dir():
        raise RestrictedRuntimeIntegrityError("RUNTIME_PACKAGE_MISSING")
    manifest_path = root / "integrity" / "SHA256SUMS.json"
    if not manifest_path.is_file():
        raise RestrictedRuntimeIntegrityError("SHA256_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text("utf-8"))
    if not isinstance(manifest, dict) or not manifest:
        raise RestrictedRuntimeIntegrityError("SHA256_MANIFEST_INVALID")
    for relative, expected in manifest.items():
        target = (root / relative).resolve()
        if root not in target.parents or not target.is_file():
            raise RestrictedRuntimeIntegrityError("MANIFEST_FILE_MISSING")
        if sha256_file(target) != expected:
            raise RestrictedRuntimeIntegrityError("PACKAGE_HASH_MISMATCH")
    config = json.loads((root / "config" / "runtime_config.json").read_text("utf-8"))
    class_map = json.loads((root / "config" / "class_to_index.json").read_text("utf-8"))
    if config.get("runtime_id") != contract["runtime_id"]:
        raise RestrictedRuntimeIntegrityError("RUNTIME_ID_MISMATCH")
    if config.get("runtime_status") != "RESTRICTED_FAIL_CLOSED_RUNTIME":
        raise RestrictedRuntimeIntegrityError("RUNTIME_STATUS_MISMATCH")
    if class_map != contract["classes"]:
        raise RestrictedRuntimeIntegrityError("CLASS_MAP_MISMATCH")
    checkpoint = root / str(config.get("checkpoint_file", ""))
    if sha256_file(checkpoint) != contract["checkpoint_sha256"]:
        raise RestrictedRuntimeIntegrityError("CHECKPOINT_HASH_MISMATCH")
    return root
