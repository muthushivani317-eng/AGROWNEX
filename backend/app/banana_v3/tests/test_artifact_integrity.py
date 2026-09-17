import hashlib
import json

import pytest
from app.banana_v3.artifact_integrity import ArtifactIntegrityError, verify_artifacts


def test_manifest_and_sums_are_verified(tmp_path):
    (tmp_path / "manifests").mkdir()
    payload = tmp_path / "model.bin"
    payload.write_bytes(b"verified")
    digest = hashlib.sha256(b"verified").hexdigest()
    (tmp_path / "manifests/artifact_manifest.json").write_text(json.dumps({
        "bundle_version": "test", "artifacts": [{"path": "model.bin", "sha256": digest}]
    }))
    (tmp_path / "manifests/SHA256SUMS.txt").write_text(f"{digest}  model.bin\n")
    assert verify_artifacts(tmp_path)["bundle_version"] == "test"
    payload.write_bytes(b"tampered")
    with pytest.raises(ArtifactIntegrityError):
        verify_artifacts(tmp_path)
