"""Single-owner policy preserves RBAC and rejects all other admin identities."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.core.config import settings
from app.modules.admin.constants import AdminRole
from app.modules.admin.exceptions import NotAnAdminError, PermissionDeniedError
from app.modules.admin.service import AdminService


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(settings, "admin_owner_firebase_uid", "pinned-owner")
    instance = AdminService(AsyncMock())
    instance.repo = SimpleNamespace(get_admin_by_user=AsyncMock())
    return instance


@pytest.mark.asyncio
async def test_only_pinned_active_owner_is_allowed(service):
    service.repo.get_admin_by_user.return_value = SimpleNamespace(role="owner", status="active")
    context = await service.resolve_admin(SimpleNamespace(id="1", firebase_uid="pinned-owner"))
    assert context.admin.role == "owner"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [role.value for role in AdminRole])
async def test_other_uid_is_denied_even_with_admin_role(service, role):
    service.repo.get_admin_by_user.return_value = SimpleNamespace(role=role, status="active")
    with pytest.raises(NotAnAdminError):
        await service.resolve_admin(SimpleNamespace(id="2", firebase_uid="other-user"))
    service.repo.get_admin_by_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_matching_uid_without_owner_role_is_denied(service):
    service.repo.get_admin_by_user.return_value = SimpleNamespace(
        role="super_admin", status="active"
    )
    with pytest.raises(NotAnAdminError):
        await service.resolve_admin(SimpleNamespace(id="1", firebase_uid="pinned-owner"))


@pytest.mark.asyncio
async def test_lockdown_blocks_new_and_existing_invitations(service):
    with pytest.raises(PermissionDeniedError):
        await service.invite_admin(None, email="other@example.com", role="super_admin")
    with pytest.raises(PermissionDeniedError):
        await service.accept_admin_invitation(None, "previously-issued-token")


@pytest.mark.asyncio
async def test_unconfigured_lockdown_preserves_team_rbac(service, monkeypatch):
    monkeypatch.setattr(settings, "admin_owner_firebase_uid", "")
    service.repo.get_admin_by_user.return_value = SimpleNamespace(
        role="super_admin", status="active"
    )
    context = await service.resolve_admin(SimpleNamespace(id="2", firebase_uid="other-user"))
    assert context.admin.role == "super_admin"
