from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.model_boundaries.router import router
from app.modules.auth.dependencies import get_current_user


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: Mock(id="test-user")
    return TestClient(app)


def test_future_model_health_is_fail_closed() -> None:
    client = _client()
    assert client.get("/disease/crop-identification/health").json()["status"] == "not_ready"
    assert client.get("/plant-identifier/health").json()["status"] == "not_ready"


def test_future_prediction_routes_never_mock_results() -> None:
    client = _client()
    files = {"image": ("leaf.jpg", b"safe-placeholder", "image/jpeg")}
    crop = client.post("/disease/crop-identification/predict", files=files)
    plant = client.post("/plant-identifier/predict", files=files)
    assert crop.status_code == 503
    assert crop.json()["detail"]["code"] == "CROP_IDENTIFICATION_MODEL_NOT_AVAILABLE"
    assert plant.status_code == 503
    assert plant.json()["detail"]["code"] == "PLANT_IDENTIFIER_MODEL_NOT_AVAILABLE"


def test_future_routes_reject_unapproved_upload_type() -> None:
    response = _client().post(
        "/plant-identifier/predict",
        files={"image": ("leaf.svg", b"<svg/>", "image/svg+xml")},
    )
    assert response.status_code == 415
