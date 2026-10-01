"""Revocation check: cached for farmers (perf), live for admin/login, never skipped."""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.core import security
from app.core.exceptions import UnauthorizedError


class Revoked(Exception):
    pass


class Disabled(Exception):
    pass


@pytest.fixture()
def fake_firebase(monkeypatch):
    state = {"lookups": 0, "valid_after_ms": 0, "disabled": False}

    def get_user(uid, app=None):
        state["lookups"] += 1
        return SimpleNamespace(disabled=state["disabled"], tokens_valid_after_timestamp=state["valid_after_ms"])

    fake_auth = SimpleNamespace(
        verify_id_token=lambda token, **kw: {"uid": "farmer-1", "iat": 1_000},
        get_user=get_user,
        RevokedIdTokenError=Revoked,
        UserDisabledError=Disabled,
        ExpiredIdTokenError=type("Expired", (Exception,), {}),
    )
    monkeypatch.setitem(sys.modules, "firebase_admin", SimpleNamespace(auth=fake_auth))
    monkeypatch.setitem(sys.modules, "firebase_admin.auth", fake_auth)
    monkeypatch.setattr(security, "_get_firebase_app", lambda: object())
    security._revocation_cache.clear()
    yield state
    security._revocation_cache.clear()


def test_farmer_requests_reuse_one_lookup(fake_firebase):
    for _ in range(5):
        assert security.verify_id_token("t")["uid"] == "farmer-1"
    assert fake_firebase["lookups"] == 1


def test_strict_paths_always_check_live_and_catch_revocation(fake_firebase):
    security.verify_id_token("t")  # cached as valid
    fake_firebase["valid_after_ms"] = 2_000_000  # tokens revoked after iat
    with pytest.raises(UnauthorizedError) as caught:
        security.verify_id_token("t", strict_revocation=True)
    assert caught.value.error_code == "TESTER_ACCESS_REVOKED"


def test_disabled_user_is_rejected(fake_firebase):
    fake_firebase["disabled"] = True
    with pytest.raises(UnauthorizedError):
        security.verify_id_token("t")


def test_lookup_outage_does_not_sign_farmers_out_but_admin_fails_closed(fake_firebase, monkeypatch):
    import firebase_admin.auth as fake_auth  # the fixture's stub

    def down(uid, app=None):
        raise ConnectionError("google unreachable")

    monkeypatch.setattr(fake_auth, "get_user", down)
    assert security.verify_id_token("t")["uid"] == "farmer-1"
    with pytest.raises(UnauthorizedError):
        security.verify_id_token("t", strict_revocation=True)
