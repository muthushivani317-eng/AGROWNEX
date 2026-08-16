from io import BytesIO
from unittest.mock import Mock

from app.banana_v3 import api_router as banana_module
from app.banana_v3.api_router import require_banana_controlled_tester
from app.banana_v3.api_router import router as banana_router
from app.crop_runtime.crop_domain import assess_crop_domain
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


def _natural_png() -> bytes:
    image = Image.effect_noise((224, 224), 25).convert("RGB")
    stream = BytesIO()
    image.save(stream, "PNG")
    return stream.getvalue()


def _client(*routers) -> TestClient:
    app = FastAPI()
    for router in routers:
        app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: Mock(id="internal-user")
    app.dependency_overrides[require_banana_controlled_tester] = lambda: Mock(
        user=Mock(id="internal-user"), role="internal_tester"
    )
    app.dependency_overrides[require_legacy_joint_controlled_tester] = lambda: Mock(
        user=Mock(id="internal-user"), role="internal_tester"
    )
    return TestClient(app)


def test_crop_domain_gate_is_explicitly_fail_closed_without_artifact() -> None:
    decision = assess_crop_domain(Image.new("RGB", (224, 224)), "paddy")
    assert decision.verified is False
    assert decision.reason_code == "CROP_IDENTITY_UNCERTAIN"


def test_all_four_crop_routes_stop_before_model_inference(monkeypatch) -> None:
    banana_predict = Mock(side_effect=AssertionError("banana runtime must not run"))
    legacy_predict = Mock(side_effect=AssertionError("legacy runtime must not run"))
    monkeypatch.setattr(banana_module._service, "predict", banana_predict)
    monkeypatch.setattr(legacy_module.runtime, "predict", legacy_predict)
    payload = _natural_png()
    client = _client(banana_router, legacy_router)
    monkeypatch.setattr(
        "app.legacy_joint.field_test_override.settings.legacy_joint_field_test_override_permitted",
        True,
    )
    legacy_module.legacy_joint_field_test_gate.activate("domain-gate-test")

    banana = client.post(
        "/disease/banana/predict",
        files={"image": ("banana.png", payload, "image/png")},
        data={"crop_confirmation_token": "forged-token"},
    )
    assert banana.status_code == 422
    assert banana.json()["detail"]["code"] == "CROP_CONFIRMATION_REQUIRED"

    try:
        for crop in ("paddy", "cotton", "groundnut"):
            response = client.post(
                f"/disease/{crop}/predict",
                files={"image": (f"{crop}.png", payload, "image/png")},
                data={
                    "crop_confirmed": "true",
                    "crop_confirmation_token": "forged-token",
                },
            )
            assert response.status_code == 422
            assert response.json()["detail"]["code"] == "CROP_CONFIRMATION_REQUIRED"
    finally:
        legacy_module.legacy_joint_field_test_gate.deactivate()

    banana_predict.assert_not_called()
    legacy_predict.assert_not_called()
