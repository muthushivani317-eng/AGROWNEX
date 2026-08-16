from app.modules.disease.capabilities import (
    CROP_CAPABILITIES,
    disease_model_available,
    normalize_crop_id,
)


def test_legacy_joint_crops_remain_disabled_until_release_audit() -> None:
    for crop in ("rice", "paddy", "cotton", "groundnut"):
        assert not disease_model_available(crop)


def test_banana_remains_independently_available() -> None:
    assert disease_model_available("banana")


def test_pipeline_pending_and_unresolved_crops_are_blocked() -> None:
    for crop in ("chilli", "redgram", "blackgram", "coconut"):
        assert not disease_model_available(crop)


def test_crop_aliases_normalize_to_stable_ids() -> None:
    assert normalize_crop_id("paddy") == "paddy"
    assert normalize_crop_id("Paddy") == "paddy"
    assert normalize_crop_id("Rice") == "paddy"
    assert normalize_crop_id("Cotton") == "cotton"
    assert normalize_crop_id("Groundnut") == "groundnut"


def test_capabilities_publish_canonical_rows_only() -> None:
    assert "paddy" in CROP_CAPABILITIES
    assert "rice" not in CROP_CAPABILITIES


def test_capability_registry_never_claims_production_approval() -> None:
    assert all(not item["production_approved"] for item in CROP_CAPABILITIES.values())
