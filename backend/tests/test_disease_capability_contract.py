from __future__ import annotations

from app.core.config import settings
from app.crop_runtime.readiness import ReadinessResolver
from app.crop_runtime.registry import load_registry
from app.modules.auth.constants import RoleName
from app.modules.disease.capability_service import (
    DiseaseCapabilitiesResponse,
    build_disease_capabilities,
)


def _rows(*, roles: set[str] | None = None):
    registry = load_registry()
    return build_disease_capabilities(
        registry=registry,
        readiness=ReadinessResolver(registry, __import__("pathlib").Path(__file__).parents[1]),
        roles=roles or set(),
        legacy_field_test_active=False,
    )


def test_farmer_capabilities_are_truthful_and_fail_closed() -> None:
    response = _rows()
    rows = {row.crop_id: row for row in response.crops}

    assert rows["banana"].runtime_ready is True
    assert rows["banana"].user_authorized is False
    assert rows["banana"].reason_unavailable == "TESTER_ROLE_REQUIRED"
    assert rows["banana"].prediction_kind == "banana_v3"
    assert rows["banana"].release_scope == "pilot"
    assert rows["banana"].adapter_available is True
    assert rows["banana"].integrity_verified is True
    assert rows["paddy"].runtime_ready is True
    assert rows["paddy"].reason_unavailable == "TESTER_ROLE_REQUIRED"
    assert all(row.general_farmer_inference_authorized is False for row in rows.values())
    assert all(row.official_accuracy_claim is False for row in rows.values())
    assert response.crop_identification.user_authorized is False
    assert response.crop_identification.reason_unavailable == "TESTER_ROLE_REQUIRED"


def test_pilot_only_gets_ready_pilot_eligible_restricted_crops() -> None:
    rows = {
        row.crop_id: row
        for row in _rows(roles={RoleName.PILOT_TESTER.value}).crops
    }

    assert rows["banana"].user_authorized is True
    assert rows["banana"].prediction_kind == "banana_v3"
    assert rows["redgram"].user_authorized is True
    assert rows["redgram"].prediction_kind == "restricted"
    assert rows["paddy"].user_authorized is False


def test_internal_tester_gets_approved_groundnut_experimental_runtime(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "groundnut_experimental_enabled", True)
    rows = {
        row.crop_id: row
        for row in _rows(roles={RoleName.INTERNAL_TESTER.value}).crops
    }

    assert rows["groundnut"].runtime_ready is True
    assert rows["groundnut"].integrity_verified is True
    assert rows["groundnut"].user_authorized is True
    assert rows["groundnut"].prediction_kind == "groundnut_experimental"
    assert rows["groundnut"].release_scope == "internal"
    assert rows["groundnut"].supported_class_ids == [
        "early_leaf_spot",
        "healthy_leaf",
        "late_leaf_spot",
        "nutrition_deficiency",
        "rust",
    ]


def test_capability_output_redacts_runtime_secrets() -> None:
    serialized = str(_rows().model_dump(mode="json"))
    for forbidden in ("runtime_path", "checkpoint_sha256", "temperature", "model_artifacts"):
        assert forbidden not in serialized


def test_conflicting_controlled_roles_match_fail_closed_auth_boundary() -> None:
    response = _rows(
        roles={RoleName.INTERNAL_TESTER.value, RoleName.PILOT_TESTER.value}
    )
    rows = response.crops
    assert all(row.user_authorized is False for row in rows)
    assert response.crop_identification.user_authorized is False
    assert all(
        row.reason_unavailable != "CONTROLLED_TESTER_AUTHORIZED" for row in rows
    )


def test_capability_response_is_a_typed_openapi_contract() -> None:
    from app.modules.disease.router import router

    route = next(route for route in router.routes if route.path == "/disease/capabilities")
    assert route.response_model is not None
    assert "DiseaseCapabilitiesResponse" in str(route.response_model)
    assert DiseaseCapabilitiesResponse.model_json_schema()["required"] == [
        "crops",
        "crop_identification",
    ]
