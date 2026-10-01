from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from app.modules.admin.constants import AdminPermission, AdminRole, permissions_for
from app.modules.admin.exceptions import FarmerNotFoundError, PermissionDeniedError
from app.modules.admin.router import router
from app.modules.admin.seed import ensure_admin
from app.modules.admin.service import AdminService
from app.modules.admin.web_security import (
    InvalidAdminOriginError,
    InvalidCsrfTokenError,
    build_csrf_token,
    require_admin_origin,
    require_csrf_token,
)
from app.modules.auth.models import User
from app.modules.auth.profile_models import FarmerProfile
from fastapi.routing import APIRoute


def test_csrf_token_is_bound_to_session_and_verified() -> None:
    token = build_csrf_token("session-a", "test-secret")
    assert token != build_csrf_token("session-b", "test-secret")
    require_csrf_token(token, token)


@pytest.mark.parametrize("provided", [None, "", "wrong"])
def test_missing_or_wrong_csrf_is_rejected(provided: str | None) -> None:
    with pytest.raises(InvalidCsrfTokenError):
        require_csrf_token(provided, "expected")


def test_exact_admin_origin_is_required_for_cookie_mutations() -> None:
    request = SimpleNamespace(headers={"origin": "https://admin.agrowai.in"})
    require_admin_origin(request, ["https://admin.agrowai.in"])
    with pytest.raises(InvalidAdminOriginError):
        require_admin_origin(
            SimpleNamespace(headers={"origin": "https://evil.example"}),
            ["https://admin.agrowai.in"],
        )


def test_origin_prefix_confusion_is_rejected() -> None:
    with pytest.raises(InvalidAdminOriginError):
        require_admin_origin(
            SimpleNamespace(headers={"origin": "https://admin.agrowai.in.evil.example"}),
            ["https://admin.agrowai.in"],
        )


def test_every_sensitive_admin_route_has_server_authorization_dependency() -> None:
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        bearer_exchange = (
            "POST" in route.methods
            and route.path in {"/admin/web-session", "/admin/invitations/accept"}
        )
        if bearer_exchange:
            continue
        parameters = inspect.signature(route.endpoint).parameters
        assert "ctx" in parameters, f"{route.path} is missing AdminContextDep"


def test_only_owner_can_manage_admin_grants() -> None:
    assert AdminPermission.MANAGE_ADMINS.value in permissions_for(AdminRole.OWNER.value)
    for role in AdminRole:
        if role != AdminRole.OWNER:
            assert AdminPermission.MANAGE_ADMINS.value not in permissions_for(role.value)


@pytest.mark.asyncio
async def test_unverified_email_cannot_accept_admin_invitation(db_session) -> None:
    owner_user = User(firebase_uid="owner", email="owner@agrowai.in", status="active")
    invited_user = User(
        firebase_uid="invitee", email="expert@agrowai.in", is_email_verified=False,
        status="active",
    )
    db_session.add_all([owner_user, invited_user])
    await db_session.flush()
    await ensure_admin(db_session, owner_user.id, role=AdminRole.OWNER.value)
    service = AdminService(db_session)
    owner = await service.resolve_admin(owner_user)
    _, token = await service.invite_admin(
        owner, email="expert@agrowai.in", role=AdminRole.AGRICULTURE_OFFICER.value
    )
    with pytest.raises(PermissionDeniedError):
        await service.accept_admin_invitation(invited_user, token)


@pytest.mark.asyncio
async def test_district_manager_cannot_read_another_district_farmer(db_session) -> None:
    manager_user = User(firebase_uid="district-admin", status="active")
    local = User(firebase_uid="local-farmer", status="active")
    remote = User(firebase_uid="remote-farmer", status="active")
    db_session.add_all([manager_user, local, remote])
    await db_session.flush()
    db_session.add_all([
        FarmerProfile(user_id=local.id, full_name="Local", district="Thanjavur"),
        FarmerProfile(user_id=remote.id, full_name="Remote", district="Madurai"),
    ])
    admin = await ensure_admin(
        db_session, manager_user.id, role=AdminRole.DISTRICT_MANAGER.value
    )
    admin.district_scope = "Thanjavur"
    await db_session.flush()
    service = AdminService(db_session)
    context = await service.resolve_admin(manager_user)
    page = await service.farmers(
        context, search=None, district="Madurai", crop=None, page=1, page_size=20
    )
    assert [row.user_id for row in page.items] == [local.id]
    with pytest.raises(FarmerNotFoundError):
        await service.farmer_detail(context, remote.id)


def test_admin_mfa_is_required_on_every_admin_path(monkeypatch) -> None:
    """A phone-OTP-only token (e.g. after a SIM swap) must not reach admin APIs.

    It must be a 403, never a 401: the farmer app signs the user out on 401,
    and every farmer's Profile tab calls GET /admin/me.
    """
    from app.core.exceptions import ForbiddenError
    from app.modules.admin import dependencies as admin_deps

    monkeypatch.setattr(admin_deps.settings, "admin_require_mfa", True)
    with pytest.raises(ForbiddenError):
        admin_deps.require_admin_mfa({"uid": "u", "firebase": {"sign_in_provider": "phone"}})
    admin_deps.require_admin_mfa(
        {"uid": "u", "firebase": {"sign_in_provider": "phone", "sign_in_second_factor": "phone"}}
    )
    source = inspect.getsource(admin_deps.get_admin_context)
    after_resolve = source.split("service.resolve_admin(")[1]
    assert "if bearer:" in after_resolve and "require_admin_mfa(claims)" in after_resolve


def test_signed_out_admin_session_cannot_be_reused() -> None:
    from app.modules.admin import dependencies as admin_deps

    cookie = "session-cookie-value-for-test"
    assert not admin_deps.is_admin_session_revoked(cookie)
    admin_deps.revoke_admin_session(cookie)
    assert admin_deps.is_admin_session_revoked(cookie)
    assert not admin_deps.is_admin_session_revoked("another-session")
