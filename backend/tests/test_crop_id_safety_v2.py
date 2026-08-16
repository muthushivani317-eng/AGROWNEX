import json
import shutil

import pytest
from app.crop_id_safety.v2 import ROOT, SafetyGateV2Error, assess_v2, verify_v2


def test_v2_is_integrity_verified_and_fail_closed():
    config = verify_v2()
    assert assess_v2(config)["outcome"] == "OOD_UNCERTAIN"
    assert config["classifier_invocation_authorized"] is False
    assert config["general_farmer_release"] == "BLOCKED"


@pytest.mark.parametrize("name", ["gate_config.json", "threshold_policy.json"])
def test_v2_tampering_fails_closed(tmp_path, name):
    target = tmp_path / "gate"
    shutil.copytree(ROOT, target)
    (target / name).write_text("{}", encoding="utf-8")
    with pytest.raises(SafetyGateV2Error):
        verify_v2(target)


def test_v2_missing_integrity_manifest_fails_closed(tmp_path):
    target = tmp_path / "gate"
    shutil.copytree(ROOT, target)
    (target / "integrity_manifest.json").unlink()
    with pytest.raises(SafetyGateV2Error):
        verify_v2(target)


def test_v2_version_mismatch_fails_closed(tmp_path):
    target = tmp_path / "gate"
    shutil.copytree(ROOT, target)
    config_path = target / "gate_config.json"
    config = json.loads(config_path.read_text())
    config["version"] = "invalid"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(SafetyGateV2Error):
        verify_v2(target)
