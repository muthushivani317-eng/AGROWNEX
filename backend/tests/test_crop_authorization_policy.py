from __future__ import annotations

from app.crop_runtime.authorization import allowed_roles, authorize_roles
from app.crop_runtime.registry import load_registry
from app.modules.auth.constants import RoleName


def test_registry_policy_controls_pilot_role_per_crop() -> None:
    registry = load_registry()
    assert RoleName.PILOT_TESTER.value in allowed_roles(registry.get("banana"))
    assert RoleName.PILOT_TESTER.value in allowed_roles(registry.get("redgram"))
    assert RoleName.PILOT_TESTER.value not in allowed_roles(registry.get("paddy"))


def test_authorization_requires_exactly_one_allowed_controlled_role() -> None:
    entry = load_registry().get("paddy")
    assert authorize_roles({RoleName.INTERNAL_TESTER.value}, entry).authorized
    assert authorize_roles({RoleName.KVK_REVIEWER.value}, entry).authorized
    assert not authorize_roles({RoleName.PILOT_TESTER.value}, entry).authorized
    assert not authorize_roles(
        {RoleName.INTERNAL_TESTER.value, RoleName.KVK_REVIEWER.value}, entry
    ).authorized
