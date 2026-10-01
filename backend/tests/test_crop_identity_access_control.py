from __future__ import annotations

import io
import sys
import uuid
from types import SimpleNamespace

import httpx
import pytest
from app.api.errors import register_exception_handlers
from app.core.database import get_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import verify_id_token
from app.crop_identity.pipeline import CropIdentityGateResult
from app.crop_identity.router import router
from app.modules.auth.constants import RoleName, UserStatus
from app.modules.auth.dependencies import (
    get_current_user,
    require_any_role,
)
from app.modules.auth.models import User
from app.modules.auth.rbac_models import Role, UserRole
from fastapi import FastAPI, HTTPException
from PIL import Image
from sqlalchemy import select

try:
    # internal_challenge_sets/ is gitignored (local-only, not shipped to CI);
    # the tests that need it are skipped there instead of failing collection.
    from internal_challenge_sets.crop_identity_v1.tools.challenge_framework import (
        ChallengeError,
        make_backend_pipeline_adapter,
    )
except ModuleNotFoundError:
    ChallengeError = None
    make_backend_pipeline_adapter = None

requires_challenge_framework = pytest.mark.skipif(
    make_backend_pipeline_adapter is None,
    reason="internal_challenge_sets is not available in this environment",
)


def png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (160, 160), (30, 120, 40)).save(output, "PNG")
    return output.getvalue()


async def user_with_role(db_session, role_name: str | None) -> User:
    user = User(
        firebase_uid=f"fixture-{uuid.uuid4()}",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()
    if role_name is not None:
        role = (
            await db_session.execute(
                select(Role).where(Role.role_name == role_name)
            )
        ).scalar_one()
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()
    return user


def app_for(db_session, user: User) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    async def session_override():
        yield db_session

    async def user_override():
        return user

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = user_override
    return app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        RoleName.INTERNAL_TESTER.value,
        RoleName.PILOT_TESTER.value,
        RoleName.KVK_REVIEWER.value,
    ],
)
async def test_controlled_roles_reach_pipeline(
    db_session, monkeypatch, role
):
    user = await user_with_role(db_session, role)
    calls = []

    async def decode(_upload):
        calls.append("decode")
        return Image.new("RGB", (160, 160), "green"), png_bytes()

    def pipeline(**_kwargs):
        calls.append("pipeline")
        return CropIdentityGateResult(
            "CROP_IDENTITY_UNCERTAIN",
            False,
            None,
            {"accepted": False, "predicted_crop": "banana"},
        )

    monkeypatch.setattr("app.crop_identity.router._decode_upload", decode)
    monkeypatch.setattr(
        "app.crop_identity.router.run_controlled_crop_identity_pipeline",
        pipeline,
    )
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post(
            "/crop-identity/predict-controlled",
            files={"image": ("image.png", png_bytes(), "image/png")},
            data={"role": "farmer"},
            headers={"X-Role": "farmer"},
        )
    assert response.status_code == 200
    assert response.json()["resolved_role"] == role
    assert response.json()["farmer_confirmation_required"] is True
    assert response.json()["confirmation_token"]
    assert response.json()["disease_adapter_called"] is False
    assert calls == ["decode", "pipeline"]


@pytest.mark.asyncio
async def test_four_class_confirmation_exchanges_suggestion_for_disease_token(
    db_session, monkeypatch
):
    user = await user_with_role(db_session, RoleName.KVK_REVIEWER.value)

    async def decode(_upload):
        return Image.new("RGB", (160, 160), "green"), png_bytes()

    def pipeline(**kwargs):
        return CropIdentityGateResult(
            "CROP_MATCH", False, None,
            {"accepted": True, "predicted_crop": "banana", "confidence": 0.99},
        )

    monkeypatch.setattr("app.crop_identity.router._decode_upload", decode)
    monkeypatch.setattr(
        "app.crop_identity.router.run_controlled_crop_identity_pipeline", pipeline
    )
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        prediction = await client.post(
            "/crop-identity/predict-controlled",
            files={"image": ("image.png", png_bytes(), "image/png")},
            data={},
        )
        suggested = prediction.json()
        confirmation = await client.post(
            "/crop-identity/confirm",
            data={
                "request_id": suggested["request_id"],
                "confirmed_crop": "banana",
                "correction": "false",
                "confirmation_token": suggested["confirmation_token"],
            },
        )
    assert prediction.status_code == 200
    assert confirmation.status_code == 200
    confirmed = confirmation.json()
    assert confirmed["status"] == "FARMER_CONFIRMED"
    assert confirmed["confirmation_token"] != suggested["confirmation_token"]
    assert confirmed["disease_routing_authorized"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role", [RoleName.FARMER.value, None, "admin"]
)
async def test_non_testers_fail_before_upload_or_models(
    db_session, monkeypatch, role
):
    user = await user_with_role(db_session, role)
    decode_called = False

    async def decode(_upload):
        nonlocal decode_called
        decode_called = True
        raise AssertionError("upload must not be decoded")

    monkeypatch.setattr("app.crop_identity.router._decode_upload", decode)
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post(
            "/crop-identity/predict-controlled?role=pilot_tester",
            files={"image": ("image.png", png_bytes(), "image/png")},
            data={"role": "internal_tester"},
            headers={"X-Role": "pilot_tester"},
        )
    assert response.status_code == 403
    assert response.json()["error_code"] == "TESTER_ROLE_REQUIRED"
    assert decode_called is False


@pytest.mark.asyncio
async def test_conflicting_controlled_roles_fail_closed(db_session):
    user = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    pilot = (
        await db_session.execute(
            select(Role).where(Role.role_name == RoleName.PILOT_TESTER.value)
        )
    ).scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=pilot.id))
    await db_session.flush()
    dependency = require_any_role(
        RoleName.INTERNAL_TESTER.value, RoleName.PILOT_TESTER.value
    )
    request = SimpleNamespace(
        url=SimpleNamespace(path="/test"),
        state=SimpleNamespace(request_id="request-1"),
    )
    with pytest.raises(ForbiddenError, match="Controlled tester"):
        await dependency(request, user, db_session)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [UserStatus.SUSPENDED, UserStatus.DELETED])
async def test_disabled_or_deleted_user_rejected(monkeypatch, status):
    from app.modules.auth.dependencies import get_current_user as resolve

    user = User(firebase_uid="disabled", status=status)
    user.deleted_at = None

    class Service:
        async def get_user_by_firebase_uid(self, _uid):
            return user

    monkeypatch.setattr(
        "app.modules.auth.dependencies.verify_id_token",
        lambda _token: {"uid": "disabled"},
    )
    with pytest.raises(UnauthorizedError):
        await resolve(SimpleNamespace(credentials="redacted"), Service())


@requires_challenge_framework
@pytest.mark.parametrize(
    "role",
    ["farmer", "admin", "", "unknown", "INTERNAL_TESTER", "*"],
)
def test_backend_challenge_adapter_rejects_non_tester_roles(role):
    with pytest.raises(ChallengeError, match="CONTROLLED_TESTER_ROLE_REQUIRED"):
        make_backend_pipeline_adapter(
            base_url="http://test",
            token_provider=lambda: "token",
            expected_role=role,
        )


@requires_challenge_framework
def test_backend_adapter_redacts_token_and_records_auth(tmp_path):
    token = "secret-fixture-token"
    image = tmp_path / "image.png"
    image.write_bytes(png_bytes())

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {
                "resolved_role": "internal_tester",
                "reason_code": "CROP_IDENTITY_UNCERTAIN",
                "crop_identity": {
                    "accepted": False,
                    "predicted_crop": "banana",
                },
                "disease_adapter_called": False,
            }

    class Client:
        def post(self, *_args, **kwargs):
            assert kwargs["headers"]["Authorization"] == f"Bearer {token}"
            return Response()

    adapter = make_backend_pipeline_adapter(
        base_url="http://test",
        token_provider=lambda: token,
        expected_role="internal_tester",
        client=Client(),
    )
    result = adapter(image, {"requested_crop": "banana"})
    assert result["authentication_outcome"] == "VERIFIED"
    assert result["token_redacted"] is True
    assert token not in str(result)


@requires_challenge_framework
def test_backend_adapter_fails_when_token_unavailable(tmp_path):
    adapter = make_backend_pipeline_adapter(
        base_url="http://test",
        token_provider=lambda: "",
        expected_role="pilot_tester",
        client=object(),
    )
    with pytest.raises(ChallengeError, match="TOKEN_UNAVAILABLE"):
        adapter(tmp_path / "unused.png", {"requested_crop": "banana"})


@pytest.mark.asyncio
async def test_missing_token_is_typed_and_fails_before_user_lookup():
    from app.modules.auth.dependencies import get_current_user as resolve

    class Service:
        async def get_user_by_firebase_uid(self, _uid):
            raise AssertionError("identity lookup must not run")

    with pytest.raises(HTTPException) as caught:
        await resolve(None, Service())
    assert caught.value.status_code == 401
    assert caught.value.detail["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.parametrize(
    ("exception_name", "expected_code"),
    [
        ("ExpiredIdTokenError", "AUTHENTICATION_EXPIRED"),
        ("RevokedIdTokenError", "TESTER_ACCESS_REVOKED"),
        ("UserDisabledError", "TESTER_ACCESS_REVOKED"),
        ("InvalidIdTokenError", "AUTHENTICATION_INVALID"),
    ],
)
def test_firebase_failure_categories_are_typed(
    monkeypatch, exception_name, expected_code
):
    exception_types = {
        name: type(name, (Exception,), {})
        for name in (
            "ExpiredIdTokenError",
            "RevokedIdTokenError",
            "UserDisabledError",
            "InvalidIdTokenError",
        )
    }

    def reject(*_args, **kwargs):
        assert kwargs["check_revoked"] is False  # revocation is checked separately (cached)
        raise exception_types[exception_name]()

    fake_auth = SimpleNamespace(
        verify_id_token=reject,
        **exception_types,
    )
    fake_firebase = SimpleNamespace(auth=fake_auth)
    monkeypatch.setitem(sys.modules, "firebase_admin", fake_firebase)
    monkeypatch.setitem(sys.modules, "firebase_admin.auth", fake_auth)
    monkeypatch.setattr("app.core.security._get_firebase_app", lambda: object())
    with pytest.raises(UnauthorizedError) as caught:
        verify_id_token("never-logged")
    assert caught.value.error_code == expected_code
