from __future__ import annotations

import uuid

import httpx
import pytest
from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.consents.models import UserConsentEvent, UserConsentState
from app.modules.consents.notices import resolve_notice
from app.modules.consents.router import router
from app.modules.consents.service import ConsentService
from fastapi import FastAPI
from sqlalchemy import func, select


async def _user(db):
    row = User(firebase_uid=f"consent-{uuid.uuid4()}", status="active")
    db.add(row)
    await db.flush()
    return row


def _app(db, user):
    app = FastAPI()
    app.include_router(router)

    async def session_override():
        yield db

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def args(purpose="marketing", key="marketing-1", granted=True):
    return dict(
        purpose=purpose,
        idempotency_key=key,
        granted=granted,
        locale="en",
        notice_version="2026-08-v1",
    )


@pytest.mark.asyncio
async def test_defaults_deny_and_allocator_versions(db_session):
    user = await _user(db_session)
    service = ConsentService(db_session)
    assert all(not x.granted for x in await service.current(user.id))
    first = await service.record(user.id, **args("optional_product_analytics", "analytics-1", True))
    second = await service.record(
        user.id, **args("optional_product_analytics", "analytics-2", False)
    )
    state = (await db_session.execute(select(UserConsentState))).scalar_one()
    assert (first.version, second.version, state.last_version) == (1, 2, 2)


@pytest.mark.asyncio
async def test_idempotency_replay_and_opposite_decision_rejected(db_session):
    user = await _user(db_session)
    service = ConsentService(db_session)
    first = await service.record(user.id, **args())
    replay = await service.record(user.id, **args())
    assert replay.version == first.version == 1
    with pytest.raises(ValueError, match="IDEMPOTENCY_KEY_REUSED"):
        await service.record(user.id, **args(granted=False))
    assert await db_session.scalar(select(func.count()).select_from(UserConsentEvent)) == 1


def test_notice_registry_is_localized_purpose_specific_and_server_hashed():
    en = resolve_notice("marketing", "en", "2026-08-v1")
    ta = resolve_notice("marketing", "ta", "2026-08-v1")
    assert en.text != ta.text and len(en.sha256) == 64 and en.sha256 != ta.sha256
    with pytest.raises(ValueError, match="NOTICE_NOT_SUPPORTED"):
        resolve_notice("marketing", "en", "unreviewed")


@pytest.mark.asyncio
async def test_api_rejects_injected_evidence_and_required_service(db_session):
    user = await _user(db_session)
    transport = httpx.ASGITransport(app=_app(db_session, user))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        initial = await client.get("/consents")
        injected = await client.post(
            "/consents/marketing/grant",
            json={
                "idempotency_key": "inject-1",
                "locale": "en",
                "notice_version": "2026-08-v1",
                "notice_hash": "fake",
            },
        )
        required = await client.post(
            "/consents/required_service/withdraw",
            json={"idempotency_key": "required-1", "locale": "en", "notice_version": "2026-08-v1"},
        )
        grant = await client.post(
            "/consents/buyer_contact_sharing/grant",
            json={"idempotency_key": "buyer-01", "locale": "ta", "notice_version": "2026-08-v1"},
        )
    assert len(initial.json()["data"]["consents"]) == 4
    assert injected.status_code == 422 and required.status_code == 422 and grant.status_code == 201
    assert grant.json()["data"]["locale"] == "ta"


@pytest.mark.asyncio
async def test_default_deny_gate_and_immutable_events(db_session):
    user = await _user(db_session)
    service = ConsentService(db_session)
    assert await service.is_granted(user.id, "precise_location") is False
    await service.record(user.id, **args("marketing", "immutable-1", True))
    row = (await db_session.execute(select(UserConsentEvent))).scalar_one()
    row.granted = False
    with pytest.raises(ValueError, match="CONSENT_EVENT_IMMUTABLE"):
        await db_session.flush()
