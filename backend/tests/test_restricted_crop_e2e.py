from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock

import httpx
import pytest
from app.api.errors import register_exception_handlers
from app.core.database import get_session
from app.gemini_crop_identification.confirmation import confirmation_store
from app.modules.auth.constants import RoleName, UserStatus
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.rbac_models import Role, UserRole
from app.restricted_crops.api_router import router
from app.disease_recommendations.router import router as recommendation_router
from fastapi import FastAPI
from PIL import Image, ImageDraw
from sqlalchemy import select


@dataclass
class Result:
    status: str
    predicted_class: str | None
    calibrated_confidence: float | None
    calibrated_margin: float | None
    abstention_code: str | None = None


class Runtime:
    def __init__(self, result: Result) -> None:
        self.result = result
        self.calls = 0

    def predict(self, _image):
        self.calls += 1
        return self.result


def image_bytes() -> bytes:
    image = Image.new("RGB", (192, 192), "green")
    draw = ImageDraw.Draw(image)
    for offset in range(0, 192, 16):
        draw.line((0, offset, 191, 191 - offset), fill="yellow", width=4)
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


async def user_with_role(db_session, role_name: str) -> User:
    user = User(firebase_uid=f"restricted-{uuid.uuid4()}", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    role = (
        await db_session.execute(select(Role).where(Role.role_name == role_name))
    ).scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()
    return user


def app_for(db_session, user: User) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.include_router(recommendation_router)

    async def session_override():
        yield db_session

    async def user_override():
        return user

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = user_override
    return app


def token_for(user: User, payload: bytes, crop_id: str) -> str:
    record = confirmation_store.create(
        actor_id=str(user.id), image=payload, identified_crop=crop_id
    )
    confirmed = confirmation_store.confirm(
        actor_id=str(user.id), request_id=record.request_id,
        confirmed_crop=crop_id, correction=False,
    )
    assert confirmed.confirmation_token
    return confirmed.confirmation_token


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("crop_id", "label"),
    [
        ("redgram", "redgram__healthy"),
        ("redgram", "redgram__sterility_mosaic"),
        ("chilli", "chilli__bacterial_spot"),
        ("chilli", "chilli__cercospora_leaf_spot"),
        ("chilli", "chilli__healthy"),
        ("chilli", "chilli__leaf_curl_virus"),
    ],
)
async def test_internal_tester_authenticated_http_accepts_exact_classes(
    db_session, monkeypatch, crop_id, label
):
    user = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    runtime = Runtime(Result("ACCEPTED_RESTRICTED_RESULT", label, 1.0, 1.0))
    monkeypatch.setattr(
        "app.restricted_crops.api_router.get_restricted_runtime",
        lambda requested: runtime if requested == crop_id else None,
    )
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    payload = image_bytes()
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/disease/{crop_id}/predict-restricted",
            files={"image": ("leaf.png", payload, "image/png")},
            data={"crop_confirmation_token": token_for(user, payload, crop_id)},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["predicted_label"] == label
    assert response.json()["recommendation_available"] is False
    assert response.json()["test_mode"]["code"] == "RESTRICTED_CROP_CONTROLLED_TEST"


@pytest.mark.asyncio
async def test_accepted_result_persists_history_fail_softly(db_session, monkeypatch):
    user = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    runtime = Runtime(Result("ACCEPTED_RESTRICTED_RESULT", "chilli__healthy", 0.91, 0.5))
    persisted = []

    async def fail_after_capture(*args, **kwargs):
        persisted.append((args, kwargs))
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(
        "app.restricted_crops.api_router.get_restricted_runtime", lambda _crop: runtime
    )
    monkeypatch.setattr(
        "app.restricted_crops.api_router.persist_controlled_test_report", fail_after_capture
    )
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    payload = image_bytes()
    farm_id = uuid.uuid4()
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/disease/chilli/predict-restricted",
            files={"image": ("leaf.png", payload, "image/png")},
            data={
                "crop_confirmation_token": token_for(user, payload, "chilli"),
                "farm_id": str(farm_id),
            },
        )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert persisted[0][1]["farm_id"] == farm_id
    assert persisted[0][1]["image"] == payload
    assert persisted[0][1]["model_used"] == "chilli_mobilenetv3_small_v1_restricted"


@pytest.mark.asyncio
@pytest.mark.parametrize("consent", [True, False])
async def test_kvk_redgram_consent_controls_retention_not_diagnosis(
    db_session, monkeypatch, consent
):
    user = await user_with_role(db_session, RoleName.KVK_REVIEWER.value)
    runtime = Runtime(
        Result("ACCEPTED_RESTRICTED_RESULT", "redgram__healthy", 0.93, 0.4)
    )
    persisted = []

    async def persist(*args, **kwargs):
        persisted.append(kwargs)
        report = type("Report", (), {})()
        report.id = uuid.uuid4()
        report.review_status = "pending" if kwargs["retain_for_review"] else "declined"
        return report

    monkeypatch.setattr(
        "app.restricted_crops.api_router.get_restricted_runtime", lambda _crop: runtime
    )
    monkeypatch.setattr(
        "app.restricted_crops.api_router.persist_controlled_test_report", persist
    )
    payload = image_bytes()
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/disease/redgram/predict-restricted",
            files={"image": ("leaf.png", payload, "image/png")},
            data={
                "crop_confirmation_token": token_for(user, payload, "redgram"),
                "kvk_session": "true",
                "review_consent": str(consent).lower(),
            },
        )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["review_status"] == ("pending" if consent else "declined")
    assert persisted[0]["retain_for_review"] is consent
    assert persisted[0]["kvk_session"] is True


@pytest.mark.asyncio
async def test_non_kvk_role_cannot_claim_kvk_session(db_session, monkeypatch):
    user = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    runtime = Runtime(
        Result("ACCEPTED_RESTRICTED_RESULT", "redgram__healthy", 0.93, 0.4)
    )
    monkeypatch.setattr(
        "app.restricted_crops.api_router.get_restricted_runtime", lambda _crop: runtime
    )
    payload = image_bytes()
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/disease/redgram/predict-restricted",
            files={"image": ("leaf.png", payload, "image/png")},
            data={
                "crop_confirmation_token": token_for(user, payload, "redgram"),
                "kvk_session": "true",
                "review_consent": "true",
            },
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_leaf_spot_abstention_does_not_persist_history(db_session, monkeypatch):
    user = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    runtime = Runtime(Result("ACCEPTED_RESTRICTED_RESULT", "redgram__leaf_spot", 1.0, 1.0))
    persist = AsyncMock()
    monkeypatch.setattr(
        "app.restricted_crops.api_router.get_restricted_runtime", lambda _crop: runtime
    )
    monkeypatch.setattr(
        "app.restricted_crops.api_router.persist_controlled_test_report", persist
    )
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    payload = image_bytes()
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/disease/redgram/predict-restricted",
            files={"image": ("leaf.png", payload, "image/png")},
            data={"crop_confirmation_token": token_for(user, payload, "redgram")},
        )
    assert response.json()["status"] == "abstained"
    persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_restricted_recommendation_requires_controlled_tester(db_session):
    tester = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    transport = httpx.ASGITransport(app=app_for(db_session, tester))
    payload = {
        "crop_id": "chilli",
        "runtime_label": "chilli__bacterial_spot",
        "diagnosis_accepted": True,
        "crop_confirmed": True,
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/disease-recommendations/lookup-restricted", json=payload)
    assert response.status_code == 200
    assert response.json()["outcome"] == "RECOMMENDATION_PARTIAL"
    assert response.json()["chemical_options"] == []


@pytest.mark.asyncio
async def test_restricted_recommendation_rejects_nonrestricted_crop(db_session):
    tester = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    transport = httpx.ASGITransport(app=app_for(db_session, tester))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/disease-recommendations/lookup-restricted",
            json={
                "crop_id": "paddy",
                "runtime_label": "rice_blast",
                "diagnosis_accepted": True,
                "crop_confirmed": True,
            },
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_farmer_cannot_use_restricted_recommendation_lookup(db_session):
    farmer = await user_with_role(db_session, RoleName.FARMER.value)
    transport = httpx.ASGITransport(app=app_for(db_session, farmer))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/disease-recommendations/lookup-restricted",
            json={
                "crop_id": "chilli",
                "runtime_label": "chilli__bacterial_spot",
                "diagnosis_accepted": True,
                "crop_confirmed": True,
            },
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_redgram_leaf_spot_http_always_abstains(db_session, monkeypatch):
    user = await user_with_role(db_session, RoleName.INTERNAL_TESTER.value)
    runtime = Runtime(
        Result("ACCEPTED_RESTRICTED_RESULT", "redgram__leaf_spot", 1.0, 1.0)
    )
    monkeypatch.setattr(
        "app.restricted_crops.api_router.get_restricted_runtime",
        lambda _crop: runtime,
    )
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    payload = image_bytes()
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/disease/redgram/predict-restricted",
            files={"image": ("leaf.png", payload, "image/png")},
            data={"crop_confirmation_token": token_for(user, payload, "redgram")},
        )
    assert response.json()["status"] == "abstained"
    assert response.json()["abstention_code"] == (
        "REDGRAM_LEAF_SPOT_AUTOMATIC_ACCEPTANCE_DISABLED"
    )


@pytest.mark.asyncio
async def test_farmer_fails_before_restricted_runtime(db_session, monkeypatch):
    user = await user_with_role(db_session, RoleName.FARMER.value)
    runtime = Runtime(
        Result("ACCEPTED_RESTRICTED_RESULT", "chilli__healthy", 1.0, 1.0)
    )
    monkeypatch.setattr(
        "app.restricted_crops.api_router.get_restricted_runtime",
        lambda _crop: runtime,
    )
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/disease/chilli/predict-restricted",
            files={"image": ("leaf.png", image_bytes(), "image/png")},
            data={"crop_confirmation_token": "not-a-valid-receipt"},
        )
    assert response.status_code == 403
    assert runtime.calls == 0
