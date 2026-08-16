from __future__ import annotations

import io
import json
import uuid

import httpx
import pytest
from app.api.errors import register_exception_handlers
from app.core.database import get_session
from app.modules.auth.constants import UserStatus
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.ai.models import TokenUsage
from app.plant_identifier.provider import PlantIdentifierProviderError
from app.plant_identifier.router import get_configured_provider, router
from app.plant_identifier.service import (
    DISCLAIMER_TA,
    InvalidPlantIdentifierResponseError,
    parse_plant_identification,
)
from fastapi import FastAPI
from PIL import Image
from sqlalchemy import select


def payload(**updates) -> str:
    value = {
        "status": "identified",
        "common_name": "Example plant",
        "scientific_name": None,
        "family": None,
        "description": "A plant with broad green leaves.",
        "visible_characteristics": ["broad green leaves"],
        "possible_alternatives": [],
        "confidence": 0.88,
        "informational_only": True,
        "used_for_disease_routing": False,
    }
    value.update(updates)
    return json.dumps(value)


def png_bytes(size: int = 160) -> bytes:
    output = io.BytesIO()
    image = Image.new("RGB", (size, size))
    image.putdata([
        (35 + (x * 2) % 160, 55 + (y * 2) % 160, 30 + ((x + y) * 2) % 160)
        for y in range(size) for x in range(size)
    ])
    image.save(output, "PNG")
    return output.getvalue()


def test_valid_identified_without_scientific_name():
    parsed = parse_plant_identification(payload())
    assert parsed.status == "identified"
    assert parsed.common_name == "Example plant"
    assert parsed.scientific_name is None


def test_valid_uncertain_and_alternatives():
    parsed = parse_plant_identification(payload(
        status="uncertain",
        common_name=None,
        confidence=0.4,
        possible_alternatives=[{
            "common_name": "Alternative",
            "scientific_name": None,
            "confidence": 0.35,
        }],
    ))
    assert parsed.status == "uncertain"
    assert len(parsed.possible_alternatives) == 1


def test_valid_non_plant_has_no_identity():
    parsed = parse_plant_identification(payload(
        status="non_plant", common_name=None, scientific_name=None,
        family=None, description=None, visible_characteristics=[],
        confidence=0.99,
    ))
    assert parsed.status == "non_plant"


def test_markdown_wrapped_json_is_validated():
    assert parse_plant_identification(f"```json\n{payload()}\n```").status == "identified"


@pytest.mark.parametrize("raw", [
    "", "not-json", "[]", payload(status="disease"),
    payload(confidence=-0.1), payload(confidence=1.1),
    payload(informational_only=False), payload(used_for_disease_routing=True),
    payload(treatment="spray something"), payload(disease="anything"),
    payload(common_name=None),
    payload(possible_alternatives=[
        {"common_name": str(i), "scientific_name": None, "confidence": 0.2}
        for i in range(6)
    ]),
])
def test_invalid_or_unsafe_provider_output_fails_closed(raw):
    with pytest.raises(InvalidPlantIdentifierResponseError):
        parse_plant_identification(raw)


async def farmer(db_session) -> User:
    user = User(firebase_uid=f"plant-id-{uuid.uuid4()}", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    return user


class Provider:
    def __init__(self, result: str | Exception):
        self.result = result
        self.called = 0

    async def identify(
        self, image: bytes, mime_type: str, language: str, note: str | None
    ) -> str:
        self.called += 1
        assert image and mime_type == "image/png"
        assert language in {"ta", "en"}
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
async def test_identified_response_is_informational_and_isolated(
    db_session, session_factory, monkeypatch
):
    monkeypatch.setattr("app.modules.ai.usage_ledger.SessionLocal", session_factory)
    user = await farmer(db_session)
    provider = Provider(payload())
    transport = httpx.ASGITransport(app=make_test_app(db_session, user, provider))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/plant-identifier/identify",
            files={"image": ("plant.png", png_bytes(), "image/png")},
            data={"preferred_language": "ta"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "identified"
    assert body["request_id"]
    assert body["informational_only"] is True
    assert body["used_for_disease_routing"] is False
    assert body["disease_inference_available"] is False
    assert body["crop_confirmation_created"] is False
    assert body["disclaimer"] == DISCLAIMER_TA
    assert "confirmed_crop_id" not in body
    usage_rows = (await db_session.execute(select(TokenUsage))).scalars().all()
    assert len(usage_rows) == 1
    assert usage_rows[0].module == "plant_identifier"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "mime"),
    [(b"", "image/png"), (b"bad", "image/png"), (b"text", "text/plain"), (None, None)],
)
async def test_invalid_upload_never_calls_provider(db_session, content, mime):
    user = await farmer(db_session)
    provider = Provider(payload())
    transport = httpx.ASGITransport(app=make_test_app(db_session, user, provider))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        kwargs = {}
        if content is not None:
            kwargs["files"] = {"image": ("bad", content, mime)}
        response = await client.post("/plant-identifier/identify", **kwargs)
    if content is None:
        assert response.status_code == 422
    else:
        assert response.status_code == 200
        assert response.json()["status"] == "invalid_image"
    assert provider.called == 0


@pytest.mark.asyncio
async def test_small_image_is_invalid_without_provider_call(db_session):
    user = await farmer(db_session)
    provider = Provider(payload())
    transport = httpx.ASGITransport(app=make_test_app(db_session, user, provider))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/plant-identifier/identify",
            files={"image": ("small.png", png_bytes(64), "image/png")},
        )
    assert response.json()["status"] == "invalid_image"
    assert provider.called == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [
    "PLANT_IDENTIFIER_PROVIDER_TIMEOUT",
    "PLANT_IDENTIFIER_PROVIDER_RATE_LIMIT",
    "PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE",
])
async def test_provider_errors_are_sanitized(db_session, code):
    user = await farmer(db_session)
    provider = Provider(PlantIdentifierProviderError(code))
    transport = httpx.ASGITransport(app=make_test_app(db_session, user, provider))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/plant-identifier/identify",
            files={"image": ("plant.png", png_bytes(), "image/png")},
        )
    body = response.json()
    assert body["status"] == "provider_error"
    assert body["error_code"] == code
    assert "traceback" not in response.text.lower()


@pytest.mark.asyncio
async def test_missing_provider_configuration_is_controlled(db_session):
    user = await farmer(db_session)
    transport = httpx.ASGITransport(app=make_test_app(db_session, user, None))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/plant-identifier/identify",
            files={"image": ("plant.png", png_bytes(), "image/png")},
        )
    assert response.json()["error_code"] == "PLANT_IDENTIFIER_PROVIDER_UNAVAILABLE"


def test_module_has_no_crop_confirmation_or_disease_service_dependency():
    from pathlib import Path

    root = Path(__file__).parents[1] / "app" / "plant_identifier"
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in root.glob("*.py")
    )
    assert "confirmed_crop" not in source
    assert "disease_service" not in source
    assert "disease_runtime" not in source
