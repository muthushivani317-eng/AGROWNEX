from __future__ import annotations

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.green_gram_experimental.router import require_green_gram_controlled_tester, router
from app.green_gram_experimental.service import get_green_gram_prediction_service


class MustNotLoad:
    def predict(self, _image):
        raise AssertionError("disabled endpoint attempted model inference")


class FakeExperimentalService:
    def predict(self, _image):
        return {
            "crop": "green_gram", "model_version": "test-exploratory", "status": "EXPERIMENTAL_RESULT",
            "predicted_class": "mymv", "confidence": 0.8,
            "top_three_predictions": [
                {"class_id": "mymv", "confidence": 0.8},
                {"class_id": "healthy", "confidence": 0.15},
                {"class_id": "leaf_curl", "confidence": 0.05},
            ],
            "supported_classes": ["healthy", "leaf_curl", "mymv"], "experimental": True,
            "expert_review_required": True, "experimental_notice": "Research only",
        }


def jpeg() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (224, 224), (20, 100, 30)).save(stream, "JPEG")
    return stream.getvalue()


def post(client: TestClient):
    return client.post(
        "/api/v1/doctor/green-gram/predict",
        files={"image": ("leaf.jpg", jpeg(), "image/jpeg")},
    )


@pytest.fixture
def authorized_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setattr(settings, "green_gram_experimental_enabled", False)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[require_green_gram_controlled_tester] = lambda: object()
    app.dependency_overrides[get_green_gram_prediction_service] = lambda: MustNotLoad()
    return app


def test_disabled_flag_returns_controlled_unavailable_without_loading_model(authorized_app: FastAPI):
    response = post(TestClient(authorized_app))
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "GREEN_GRAM_MODEL_NOT_AVAILABLE"


def test_route_requires_authentication(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "green_gram_experimental_enabled", False)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    response = post(TestClient(app))
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_enabled_route_returns_explicit_experimental_contract(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "green_gram_experimental_enabled", True)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[require_green_gram_controlled_tester] = lambda: object()
    app.dependency_overrides[get_green_gram_prediction_service] = lambda: FakeExperimentalService()
    response = post(TestClient(app))
    assert response.status_code == 200
    body = response.json()
    assert body["experimental"] is True
    assert body["expert_review_required"] is True
    assert body["supported_classes"] == ["healthy", "leaf_curl", "mymv"]


def test_enabled_route_rejects_unsupported_file(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "green_gram_experimental_enabled", True)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[require_green_gram_controlled_tester] = lambda: object()
    response = TestClient(app).post(
        "/api/v1/doctor/green-gram/predict", files={"image": ("leaf.gif", b"GIF89a", "image/gif")}
    )
    assert response.status_code == 415


def test_enabled_route_rejects_corrupted_image(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "green_gram_experimental_enabled", True)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[require_green_gram_controlled_tester] = lambda: object()
    response = TestClient(app).post(
        "/api/v1/doctor/green-gram/predict", files={"image": ("leaf.jpg", b"not-an-image", "image/jpeg")}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GREEN_GRAM_IMAGE_CORRUPTED"


def test_enabled_route_rejects_oversized_upload(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "green_gram_experimental_enabled", True)
    monkeypatch.setattr(settings, "green_gram_max_upload_bytes", 64)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[require_green_gram_controlled_tester] = lambda: object()
    response = TestClient(app).post(
        "/api/v1/doctor/green-gram/predict", files={"image": ("leaf.jpg", b"x" * 65, "image/jpeg")}
    )
    assert response.status_code == 413
