"""Shared registry-aware role policy for crop inference."""
from __future__ import annotations

from dataclasses import dataclass

from app.modules.auth.constants import RoleName

from .schemas import CropRegistryEntry


@dataclass(frozen=True)
class RoleAuthorization:
    authorized: bool
    resolved_role: str | None
    reason: str | None


def allowed_roles(entry: CropRegistryEntry) -> frozenset[str]:
    roles = {
        RoleName.INTERNAL_TESTER.value,
        RoleName.KVK_REVIEWER.value,
    }
    if entry.pilot_inference_eligible:
        roles.add(RoleName.PILOT_TESTER.value)
    return frozenset(roles)


def authorize_roles(roles: set[str], entry: CropRegistryEntry) -> RoleAuthorization:
    controlled = roles & {
        RoleName.INTERNAL_TESTER.value,
        RoleName.PILOT_TESTER.value,
        RoleName.KVK_REVIEWER.value,
    }
    if len(controlled) != 1:
        return RoleAuthorization(False, None, "TESTER_ROLE_REQUIRED")
    role = next(iter(controlled))
    if role not in allowed_roles(entry):
        return RoleAuthorization(False, role, "MODEL_RELEASE_NOT_AUTHORIZED")
    return RoleAuthorization(True, role, None)
