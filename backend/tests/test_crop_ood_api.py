from io import BytesIO
from unittest.mock import Mock

from app.banana_v3.api_router import require_banana_controlled_tester
from app.banana_v3.api_router import router as banana_router
from app.gemini_crop_identification.confirmation import confirmation_store
from app.legacy_joint import api_router as legacy_module
from app.legacy_joint.api_router import (
    require_legacy_joint_controlled_tester,
)
from app.legacy_joint.api_router import (
    router as legacy_router,
)
from app.modules.auth.dependencies import get_current_user
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image


def uniform_png() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (224, 224), (40, 180, 40)).save(stream, "PNG")
    return stream.getvalue()


def app_for(router) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: Mock(id="internal-user")
    app.dependency_overrides[require_banana_controlled_tester] = lambda: Mock(
        user=Mock(id="internal-user"), role="internal_tester"
    )
    app.dependency_overrides[require_legacy_joint_controlled_tester] = lambda: Mock(
        user=Mock(id="internal-user"), role="internal_tester"
    )
    return TestClient(app)


def token_for(payload: bytes, crop: str) -> str:
    record = confirmation_store.create(
        actor_id="internal-user", image=payload, identified_crop=crop
    )
    confirmed = confirmation_store.confirm(
        actor_id="internal-user", request_id=record.request_id,
        confirmed_crop=crop, correction=False,
    )
    assert confirmed.confirmation_token
    return confirmed.confirmation_token


def test_banana_uniform_ood_is_rejected_before_disease_output() -> None:
    payload = uniform_png()
    response = app_for(banana_router).post(
        "/disease/banana/predict",
        files={"image": ("uniform.png", payload, "image/png")},
        data={"crop_confirmation_token": token_for(payload, "banana")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["decision_code"] == "BV3_OUT_OF_DOMAIN_IMAGE"
    assert response.json()["result"]["class_id"] is None


def test_banana_corrupt_uploads_return_controlled_errors() -> None:
    client = app_for(banana_router)
    for name, payload, content_type in (
        ("corrupt.jpg", b"not-a-jpeg", "image/jpeg"),
        ("truncated.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/jpeg"),
        ("truncated.png", b"\x89PNG\r\n\x1a\n\x00\x00", "image/png"),
        ("invalid.jpg", b"\x00\x01\x02\x03", "image/jpeg"),
    ):
        response = client.post(
            "/disease/banana/predict",
            files={"image": (name, payload, content_type)},
            data={"crop_confirmation_token": token_for(payload, "banana")},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "BV3_IMAGE_UNREADABLE"


def test_banana_empty_upload_returns_controlled_4xx() -> None:
    payload = b""
    response = app_for(banana_router).post(
        "/disease/banana/predict",
        files={"image": ("empty.jpg", payload, "image/jpeg")},
        data={"crop_confirmation_token": token_for(payload, "banana")},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "BV3_IMAGE_UNREADABLE"


def test_banana_unsupported_format_and_malformed_multipart_are_client_errors() -> None:
    client = app_for(banana_router)
    unsupported = client.post(
        "/disease/banana/predict",
        files={"image": ("image.gif", b"GIF89a", "image/gif")},
        data={"crop_confirmation_token": token_for(b"GIF89a", "banana")},
    )
    assert unsupported.status_code == 415
    assert unsupported.json()["detail"]["code"] == "BV3_IMAGE_FORMAT_UNSUPPORTED"

    malformed = client.post(
        "/disease/banana/predict",
        content=b"not-multipart",
        headers={"content-type": "multipart/form-data; boundary=missing"},
    )
    assert 400 <= malformed.status_code < 500


def test_paddy_cotton_and_groundnut_uniform_ood_are_rejected(monkeypatch) -> None:
    client = app_for(legacy_router)
    monkeypatch.setattr(
        "app.legacy_joint.field_test_override.settings.legacy_joint_field_test_override_permitted",
        True,
    )
    legacy_module.legacy_joint_field_test_gate.activate("ood-api-test")
    try:
        for crop in ("paddy", "cotton", "groundnut"):
            payload = uniform_png()
            response = client.post(
                f"/disease/{crop}/predict",
                files={"image": ("uniform.png", payload, "image/png")},
                data={
                    "crop_confirmed": "true",
                    "crop_confirmation_token": token_for(payload, crop),
                },
            )
            assert response.status_code == 422
            assert response.json()["detail"]["code"] == "OUT_OF_DOMAIN_IMAGE"
    finally:
        legacy_module.legacy_joint_field_test_gate.deactivate()
