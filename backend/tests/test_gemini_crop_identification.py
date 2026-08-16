from __future__ import annotations

import io
import json
import uuid

import httpx
import pytest
from app.api.errors import register_exception_handlers
from app.core.database import get_session
from app.gemini_crop_identification.confirmation import ConfirmationError, ConfirmationStore
from app.gemini_crop_identification.provider import CropIdentificationProviderError
from app.gemini_crop_identification.router import get_configured_provider, router
from app.gemini_crop_identification.service import (
    IDENTIFICATION_THRESHOLD,
    InvalidGeminiCropResponseError,
    parse_crop_identification,
)
from app.modules.auth.constants import RoleName, UserStatus
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.rbac_models import Role, UserRole
from fastapi import FastAPI
from PIL import Image
from sqlalchemy import select


def payload(**updates) -> str:
    value = {
        "status": "identified",
        "crop_id": "chilli",
        "confidence": 0.96,
        "confidence_available": True,
        "reason_code": "VISUAL_CROP_MATCH",
        "plant_outcome": "plant",
        "needs_another_image": False,
    }
    value.update(updates)
    return json.dumps(value)


def png_bytes() -> bytes:
    output = io.BytesIO()
    image = Image.new("RGB", (160, 160))
    image.putdata(
        [
            (35 + (x * 2) % 160, 55 + (y * 2) % 160, 30 + ((x + y) * 2) % 160)
            for y in range(160)
            for x in range(160)
        ]
    )
    image.save(output, "PNG")
    return output.getvalue()


@pytest.mark.parametrize("crop", ["banana", "paddy", "cotton", "groundnut", "redgram", "chilli"])
def test_only_six_supported_crop_ids_are_identified(crop):
    result = parse_crop_identification(payload(crop_id=crop))
    assert result.status == "identified"
    assert result.crop_id == crop


def test_low_confidence_and_unavailable_confidence_fail_closed():
    assert (
        parse_crop_identification(payload(confidence=IDENTIFICATION_THRESHOLD - 1e-12)).status
        == "uncertain"
    )
    result = parse_crop_identification(payload(confidence=None, confidence_available=False))
    assert result.status == "uncertain"
    assert result.crop_id is None


@pytest.mark.parametrize(
    "raw",
    [
        "chilli",
        "{}",
        payload(crop_id="tomato"),
        payload(confidence=1.1),
        payload(extra="injection"),
    ],
)
def test_malformed_arbitrary_or_extra_provider_output_is_rejected(raw):
    with pytest.raises(InvalidGeminiCropResponseError):
        parse_crop_identification(raw)


def test_confirmation_receipt_binds_image_crop_owner_and_blocks_replay():
    store = ConfirmationStore()
    image = b"original-image"
    record = store.create(actor_id="actor-a", image=image, identified_crop="banana")
    confirmed = store.confirm(
        actor_id="actor-a",
        request_id=record.request_id,
        confirmed_crop="banana",
        correction=False,
    )
    assert confirmed.confirmation_token
    store.validate(
        actor_id="actor-a",
        token=confirmed.confirmation_token,
        crop="banana",
        image=image,
    )
    with pytest.raises(ConfirmationError, match="CROP_CONFIRMATION_REPLAYED"):
        store.validate(
            actor_id="actor-a",
            token=confirmed.confirmation_token,
            crop="banana",
            image=image,
        )


async def user_with_role(db_session, role_name: str) -> User:
    user = User(firebase_uid=f"crop-id-{uuid.uuid4()}", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    role = (await db_session.execute(select(Role).where(Role.role_name == role_name))).scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()
    return user


class Provider:
    model_name = "gemini-test-model"

    def __init__(self, result: str | Exception):
        self.result = result
        self.called = 0

    async def identify(self, image: bytes, mime_type: str) -> str:
        self.called += 1
        assert image and mime_type == "image/png"
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def make_test_app(db_session, user, provider) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    async def session_override():
        yield db_session

    async def user_override():
        return user

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = user_override
    app.dependency_overrides[get_configured_provider] = lambda: provider
    return app


@pytest.mark.asyncio
async def test_identification_contract_and_server_confirmation(db_session):
    user = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    provider = Provider(payload())
    transport = httpx.ASGITransport(app=make_test_app(db_session, user, provider))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/crop-identification", files={"image": ("crop.png", png_bytes(), "image/png")}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["identified_crop"] == "chilli"
        assert body["farmer_confirmation_required"] is True
        assert body["confidence_source"] == "gemini_self_report"
        assert body["plant_check"]["method"] == "temporary_gemini_provider_assisted"
        assert "visible_evidence" not in body
        confirmed = await client.post(
            "/crop-identification/confirm",
            json={
                "request_id": body["request_id"],
                "confirmed_crop": "chilli",
                "decision": "confirmed",
            },
        )
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["crop_source"] == "gemini_confirmed"
        assert len(confirmed.json()["confirmation_token"]) >= 32


@pytest.mark.asyncio
async def test_confirmation_rejects_cross_user_and_wrong_crop(db_session):
    first = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    second = await user_with_role(db_session, RoleName.PILOT_TESTER.value)
    provider = Provider(payload())
    app = make_test_app(db_session, first, provider)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        identified = (
            await client.post(
                "/crop-identification", files={"image": ("crop.png", png_bytes(), "image/png")}
            )
        ).json()
        wrong = await client.post(
            "/crop-identification/confirm",
            json={
                "request_id": identified["request_id"],
                "confirmed_crop": "banana",
                "decision": "confirmed",
            },
        )
        assert wrong.status_code == 422
        app.dependency_overrides[get_current_user] = lambda: second
        cross_user = await client.post(
            "/crop-identification/confirm",
            json={
                "request_id": identified["request_id"],
                "confirmed_crop": "chilli",
                "decision": "confirmed",
            },
        )
        assert cross_user.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "mime", "status"),
    [(b"not an image", "image/png", 422), (b"text", "text/plain", 415)],
)
async def test_invalid_upload_never_reaches_provider(db_session, content, mime, status):
    user = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    provider = Provider(payload())
    transport = httpx.ASGITransport(app=make_test_app(db_session, user, provider))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/crop-identification", files={"image": ("bad", content, mime)}
        )
    assert response.status_code == status and provider.called == 0


@pytest.mark.asyncio
async def test_provider_failure_is_controlled(db_session):
    user = await user_with_role(db_session, RoleName.PILOT_TESTER.value)
    provider = Provider(CropIdentificationProviderError("GEMINI_REQUEST_FAILED"))
    transport = httpx.ASGITransport(app=make_test_app(db_session, user, provider))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/crop-identification", files={"image": ("crop.png", png_bytes(), "image/png")}
        )
    assert response.status_code == 502
    assert "api_key" not in response.text.lower()
