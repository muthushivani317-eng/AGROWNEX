"""User-aware disease capabilities derived from the frozen crop registry.

This module is intentionally the only adapter between release policy, verified
runtime readiness, and the authenticated user's controlled-testing roles.
"""
from __future__ import annotations

import asyncio

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.crop_identity_six_class_internal.runtime import (
    CLASSES as CROP_IDENTITY_CLASSES,
)
from app.crop_runtime.authorization import authorize_roles
from app.crop_runtime.inventory import get_model_inventory
from app.crop_runtime.readiness import ReadinessResolver
from app.crop_runtime.readiness_cache import get_technical_readiness
from app.crop_runtime.registry import CropRegistry, load_registry
from app.legacy_joint.field_test_override import legacy_joint_field_test_gate
from app.modules.auth.constants import RoleName
from app.modules.auth.models import User
from app.modules.auth.repositories import RoleRepository

CONTROLLED_ROLES = {
    RoleName.INTERNAL_TESTER.value,
    RoleName.PILOT_TESTER.value,
    RoleName.KVK_REVIEWER.value,
}
LEGACY_CROPS = {"paddy", "cotton", "groundnut"}
PREDICTION_KINDS = {
    "banana": "banana_v3",
    "paddy": "legacy_joint",
    "cotton": "legacy_joint",
    "groundnut": "legacy_joint",
    "chilli": "restricted",
    "redgram": "restricted",
}


class DiseaseCapability(BaseModel):
    crop_id: str
    display_name_en: str
    display_name_ta: str
    visible: bool
    runtime_ready: bool
    integrity_verified: bool
    adapter_available: bool
    user_authorized: bool
    release_scope: str
    supported_class_ids: list[str]
    prediction_kind: str | None
    field_validation_status: str
    reason_unavailable: str | None
    farmer_confirmation_required: bool = True
    general_farmer_inference_authorized: bool = False
    official_accuracy_claim: bool = False


class CropIdentificationCapability(BaseModel):
    visible: bool = True
    runtime_ready: bool
    integrity_verified: bool
    adapter_available: bool = True
    user_authorized: bool
    release_scope: str = "pilot"
    supported_class_ids: list[str]
    prediction_kind: str = "six_class"
    reason_unavailable: str | None
    farmer_confirmation_required: bool = True
    general_farmer_inference_authorized: bool = False
    official_accuracy_claim: bool = False


class DiseaseCapabilitiesResponse(BaseModel):
    crops: list[DiseaseCapability]
    crop_identification: CropIdentificationCapability


def _runtime_failure_reason(result) -> str:
    if not result.artifact_present:
        return "MODEL_ARTIFACT_MISSING"
    if not result.integrity_verified:
        return "MODEL_INTEGRITY_FAILURE"
    return "MODEL_RUNTIME_UNAVAILABLE"


def build_disease_capabilities(
    *,
    registry: CropRegistry,
    readiness: ReadinessResolver | None,
    roles: set[str],
    legacy_field_test_active: bool,
    technical_readiness: dict | None = None,
    crop_identity_ready: bool | None = None,
) -> DiseaseCapabilitiesResponse:
    controlled_roles = roles & CONTROLLED_ROLES
    rows: list[DiseaseCapability] = []
    for entry in registry.document.crops:
        result = (
            technical_readiness[entry.crop_id]
            if technical_readiness is not None
            else readiness.resolve(entry.crop_id)  # type: ignore[union-attr]
        )
        runtime_ready = result.runtime_loadable
        prediction_kind = PREDICTION_KINDS.get(entry.crop_id)
        role_policy = authorize_roles(roles, entry)
        authorized = bool(role_policy.authorized and runtime_ready and prediction_kind)
        reason: str | None = None

        if not runtime_ready:
            authorized = False
            reason = _runtime_failure_reason(result)
        elif not role_policy.authorized:
            authorized = False
            reason = role_policy.reason
        elif entry.crop_id in LEGACY_CROPS and not legacy_field_test_active:
            authorized = False
            reason = "LEGACY_FIELD_TEST_SESSION_REQUIRED"
        elif prediction_kind is None:
            authorized = False
            reason = "MODEL_RELEASE_NOT_AUTHORIZED"

        release_scope = (
            "pilot"
            if entry.crop_id in {"banana", "chilli", "redgram"}
            else "internal"
            if prediction_kind == "legacy_joint"
            else "blocked"
        )
        rows.append(
            DiseaseCapability(
                crop_id=entry.crop_id,
                display_name_en=entry.display_name_en,
                display_name_ta=entry.display_name_ta,
                visible=entry.crop_enabled,
                runtime_ready=runtime_ready,
                integrity_verified=result.integrity_verified,
                adapter_available=prediction_kind is not None,
                user_authorized=authorized,
                release_scope=release_scope,
                supported_class_ids=list(entry.supported_classes),
                prediction_kind=prediction_kind,
                field_validation_status=entry.field_validation_status,
                reason_unavailable=reason,
            )
        )
    identity_integrity = (
        crop_identity_ready
        if crop_identity_ready is not None
        else get_model_inventory().crop_identity_ready
        and get_model_inventory().safety_gate_ready
    )
    identity_authorized = identity_integrity and len(controlled_roles) == 1
    identity_reason = (
        None
        if identity_authorized
        else "MODEL_RUNTIME_UNAVAILABLE"
        if not identity_integrity
        else "TESTER_ROLE_REQUIRED"
    )
    return DiseaseCapabilitiesResponse(
        crops=rows,
        crop_identification=CropIdentificationCapability(
            runtime_ready=identity_integrity,
            integrity_verified=identity_integrity,
            user_authorized=identity_authorized,
            supported_class_ids=list(CROP_IDENTITY_CLASSES),
            reason_unavailable=identity_reason,
        ),
    )


async def disease_capabilities_for_user(
    user: User,
    session: AsyncSession,
) -> DiseaseCapabilitiesResponse:
    roles = set(await RoleRepository(session).get_user_role_names(user.id))
    registry = load_registry()
    readiness, inventory = await asyncio.gather(
        asyncio.to_thread(get_technical_readiness),
        asyncio.to_thread(get_model_inventory),
    )
    return build_disease_capabilities(
        registry=registry,
        readiness=None,
        roles=roles,
        legacy_field_test_active=legacy_joint_field_test_gate.status()["active"],
        technical_readiness=readiness,
        crop_identity_ready=(
            inventory.crop_identity_ready and inventory.safety_gate_ready
        ),
    )
