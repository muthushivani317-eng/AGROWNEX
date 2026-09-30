"""Farmer deletion stays in step with Firebase Authentication (both directions)."""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.admin import farmer_deletion
from app.modules.admin.constants import AdminRole, permissions_for
from app.modules.admin.farmer_deletion import admin_delete_farmer, sync_deleted_firebase_users
from app.modules.admin.models import AdminUser, AuditLog
from app.modules.admin.queries import AdminQueries
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.profile_models import FarmerProfile
from app.modules.farms.models import Farm


async def _farmer(db_session, uid: str) -> User:
    user = User(firebase_uid=uid, status="active", phone_number="+919000000000")
    db_session.add(user)
    await db_session.flush()
    db_session.add_all(
        [
            FarmerProfile(user_id=user.id, full_name=uid, district="Thoothukudi"),
            Farm(user_id=user.id, name=f"{uid} farm", crop="banana"),
            RefreshToken(user_id=user.id, token_hash=uuid.uuid4().hex, expires_at=datetime(2030, 1, 1)),
        ]
    )
    await db_session.flush()
    return user


async def _owner(db_session):
    from app.modules.admin.service import AdminContext

    user = User(firebase_uid=f"owner-{uuid.uuid4()}", status="active")
    db_session.add(user)
    await db_session.flush()
    admin = AdminUser(user_id=user.id, role=AdminRole.OWNER.value)
    db_session.add(admin)
    await db_session.flush()
    return AdminContext(admin=admin, permissions=frozenset(permissions_for(AdminRole.OWNER.value)))


async def _directory_refs(db_session) -> set[str]:
    rows, _ = await AdminQueries(db_session).farmers()
    return {row.farmer_ref for row in rows}


@pytest.mark.asyncio
async def test_admin_delete_removes_firebase_account_then_hides_farmer(db_session, monkeypatch):
    deleted: list[str] = []
    monkeypatch.setattr(farmer_deletion, "delete_firebase_account", lambda uid: deleted.append(uid) or True)
    owner = await _owner(db_session)
    farmer = await _farmer(db_session, "ttt")
    await db_session.commit()

    with pytest.raises(ConflictError):
        await admin_delete_farmer(db_session, owner, farmer.id, confirm_ref="AGF-WRONG")
    assert deleted == []

    result = await admin_delete_farmer(db_session, owner, farmer.id, confirm_ref=farmer.farmer_ref.lower())
    assert result["deleted"] is True and deleted == ["ttt"]
    await db_session.refresh(farmer)
    assert farmer.status == "deleted" and farmer.deleted_at is not None
    assert farmer.farmer_ref not in await _directory_refs(db_session)
    token = (await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == farmer.id))).scalar_one()
    assert token.revoked is True
    audit = (await db_session.execute(select(AuditLog).where(AuditLog.action == "farmer_deleted"))).scalar_one()
    assert audit.meta["farmer_ref"] == farmer.farmer_ref

    with pytest.raises(NotFoundError):
        await admin_delete_farmer(db_session, owner, farmer.id, confirm_ref=farmer.farmer_ref)


@pytest.mark.asyncio
async def test_admin_account_cannot_be_deleted_from_farmer_directory(db_session, monkeypatch):
    monkeypatch.setattr(farmer_deletion, "delete_firebase_account", lambda uid: pytest.fail("must not call Firebase"))
    owner = await _owner(db_session)
    owner_user = await db_session.get(User, owner.admin.user_id)
    await db_session.commit()
    with pytest.raises(ConflictError):
        await admin_delete_farmer(db_session, owner, owner_user.id, confirm_ref=owner_user.farmer_ref)


@pytest.mark.asyncio
async def test_sync_closes_farmers_deleted_in_firebase(db_session, monkeypatch):
    owner = await _owner(db_session)
    keep = [await _farmer(db_session, f"keep-{i}") for i in range(4)]
    gone = await _farmer(db_session, "gone-in-firebase")
    await db_session.commit()
    monkeypatch.setattr(farmer_deletion, "firebase_missing_uids", lambda uids: {"gone-in-firebase"})

    result = await sync_deleted_firebase_users(db_session, actor_admin=owner)

    assert result.closed == 1 and not result.aborted
    refs = await _directory_refs(db_session)
    assert gone.farmer_ref not in refs
    assert all(user.farmer_ref in refs for user in keep)


@pytest.mark.asyncio
async def test_sync_aborts_when_too_many_users_look_missing(db_session, monkeypatch):
    users = [await _farmer(db_session, f"u-{i}") for i in range(6)]
    await db_session.commit()
    monkeypatch.setattr(farmer_deletion, "firebase_missing_uids", lambda uids: set(uids))

    result = await sync_deleted_firebase_users(db_session)

    assert result.aborted is True and result.closed == 0
    refs = await _directory_refs(db_session)
    assert all(user.farmer_ref in refs for user in users)
