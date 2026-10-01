"""Permanent erasure of closed accounts 30 days after closure."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.modules.admin import account_purge
from app.modules.admin.models import AdminUser
from app.modules.ai.models import AIConversation, AIMessage
from app.modules.auth.models import User
from app.modules.auth.profile_models import FarmerProfile
from app.modules.consents.models import UserConsentEvent
from app.modules.disease import storage as storage_module
from app.modules.disease.models import DiseaseReport
from app.modules.farms.models import Farm

NOW = datetime(2026, 10, 1, tzinfo=UTC)

# Production has every table (migrations); load all models before the test DB is created.
account_purge._load_all_models()


@pytest.fixture()
def store(monkeypatch):
    mock = storage_module.MockStorage()
    monkeypatch.setattr(storage_module, "get_default_storage", lambda: mock)
    monkeypatch.setattr(storage_module, "get_private_storage", lambda: mock)
    return mock


async def _farmer(db, *, closed_days_ago: int | None, phone: str) -> User:
    user = User(firebase_uid=f"fb-{uuid.uuid4()}", status="active", phone_number=phone)
    if closed_days_ago is not None:
        user.status = "deleted"
        user.is_deleted = True
        user.deleted_at = NOW - timedelta(days=closed_days_ago)
    db.add(user)
    await db.flush()
    farm = Farm(user_id=user.id, name="North field")
    db.add(farm)
    await db.flush()
    convo = AIConversation(user_id=user.id, language="ta")
    db.add(convo)
    await db.flush()
    db.add(AIMessage(conversation_id=convo.id, sender="user", message="paddy leaf spots"))
    db.add(DiseaseReport(user_id=user.id, farm_id=farm.id, image_key=f"disease/farmer/{user.id}/leaf.jpg"))
    db.add(UserConsentEvent(
        user_id=user.id, purpose="profile", granted=True, version=1, idempotency_key=str(uuid.uuid4()),
        policy_version="2026-09", notice_hash="0" * 64, channel="app", locale="ta",
    ))
    await db.flush()
    return user


async def _count(db, model, **where) -> int:
    stmt = select(model)
    for key, value in where.items():
        stmt = stmt.where(getattr(model, key) == value)
    return len((await db.execute(stmt)).scalars().all())


async def test_purges_personal_data_after_30_days_and_keeps_consent_receipts(db_session, store):
    user = await _farmer(db_session, closed_days_ago=31, phone="+919000000001")
    store.objects[f"disease/farmer/{user.id}/leaf.jpg"] = b"img"

    result = await account_purge.purge_closed_accounts(db_session, now=NOW, delete_firebase=False)

    assert result["users"] == 1 and result["media_deleted"] == 1
    for model in (Farm, AIConversation, DiseaseReport):
        assert await _count(db_session, model, user_id=user.id) == 0
    assert await _count(db_session, AIMessage) == 0
    assert await _count(db_session, UserConsentEvent, user_id=user.id) == 1
    await db_session.refresh(user)
    assert user.phone_number is None and account_purge.is_purged(user)
    assert store.objects == {}


async def test_recent_closures_active_users_and_admins_are_untouched(db_session, store):
    recent = await _farmer(db_session, closed_days_ago=10, phone="+919000000002")
    active = await _farmer(db_session, closed_days_ago=None, phone="+919000000003")
    admin = await _farmer(db_session, closed_days_ago=90, phone="+919000000004")
    db_session.add(AdminUser(user_id=admin.id, role="super_admin"))
    await db_session.flush()

    result = await account_purge.purge_closed_accounts(db_session, now=NOW, delete_firebase=False)

    assert result["users"] == 0
    for user in (recent, active, admin):
        assert await _count(db_session, Farm, user_id=user.id) == 1
        await db_session.refresh(user)
        assert user.phone_number and not account_purge.is_purged(user)


async def test_purge_is_idempotent(db_session, store):
    await _farmer(db_session, closed_days_ago=45, phone="+919000000005")

    first = await account_purge.purge_closed_accounts(db_session, now=NOW, delete_firebase=False)
    second = await account_purge.purge_closed_accounts(db_session, now=NOW, delete_firebase=False)

    assert first["users"] == 1 and second["users"] == 0


async def test_purge_never_deletes_files_the_user_does_not_own(db_session, store, monkeypatch):
    """A farmer-typed profile_photo URL must not let the purge delete someone else's file."""
    from app.modules.disease import constants as disease_constants

    monkeypatch.setattr(disease_constants, "R2_PUBLIC_BASE_URL", "https://cdn.example")
    victim_key = f"disease/farmer/{uuid.uuid4()}/victim.jpg"
    store.objects[victim_key] = b"victim"
    attacker = await _farmer(db_session, closed_days_ago=40, phone="+919000000006")
    db_session.add(FarmerProfile(user_id=attacker.id, profile_photo=f"https://cdn.example/{victim_key}"))
    await db_session.flush()

    await account_purge.purge_closed_accounts(db_session, now=NOW, delete_firebase=False)

    assert victim_key in store.objects


def test_only_plain_keys_scoped_to_owned_ids_are_deleted():
    purger = account_purge._Purger(None, {}, ())
    owner = str(uuid.uuid4())
    purger.owned_ids.add(owner)
    purger.media = {
        f"disease/farmer/{owner}/a.jpg",
        f"profiles/{owner}/../disease/farmer/victim/x.jpg",
        f"profiles/{owner}/%2e%2e/x.jpg",
        "disease/farmer/someone-else/b.jpg",
    }
    assert purger.owned_media() == {f"disease/farmer/{owner}/a.jpg"}
