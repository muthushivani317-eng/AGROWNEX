from types import SimpleNamespace

import pytest
from app.core.config import settings
from app.modules.admin.exceptions import PermissionDeniedError
from app.modules.admin.router import get_team_access_policy


@pytest.mark.asyncio
async def test_policy_requires_owner_even_with_permission():
    ctx = SimpleNamespace(admin=SimpleNamespace(role="super_admin"), permissions={"manage_admins"})
    with pytest.raises(PermissionDeniedError):
        await get_team_access_policy(ctx)


@pytest.mark.asyncio
async def test_policy_requires_permission():
    ctx = SimpleNamespace(admin=SimpleNamespace(role="owner"), permissions=set())
    with pytest.raises(PermissionDeniedError):
        await get_team_access_policy(ctx)


@pytest.mark.asyncio
async def test_policy_reports_flags_and_roles_without_owner_uid(monkeypatch):
    monkeypatch.setattr(settings, "admin_owner_firebase_uid", "private-owner-uid")
    monkeypatch.setattr(settings, "admin_require_mfa", True)
    ctx = SimpleNamespace(admin=SimpleNamespace(role="owner"), permissions={"manage_admins"})
    result = await get_team_access_policy(ctx)
    assert result.data["owner_only"] is True
    assert result.data["mfa_required"] is True
    assert "reveal_buyer_contact" in result.data["roles"]["procurement_manager"]
    assert "private-owner-uid" not in str(result)
