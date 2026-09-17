from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.core.database import get_session
from app.legacy_joint import api_router as api
from app.legacy_joint.api_router import require_legacy_joint_controlled_tester, router
from app.legacy_joint.runtime import JointPrediction


def test_prediction_is_returned_when_history_persistence_fails(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_legacy_joint_controlled_tester] = lambda: SimpleNamespace(
        user=SimpleNamespace(id="tester"), role="kvk_reviewer"
    )

    async def session_override():
        yield object()

    app.dependency_overrides[get_session] = session_override

    async def decoded_image(*_args, **_kwargs):
        return Image.new("RGB", (224, 224)), b"image", "image/png"

    async def persistence_failure(*_args, **_kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(api, "_image", decoded_image)
    monkeypatch.setattr(api, "persist_controlled_test_report", persistence_failure)
    monkeypatch.setattr(
        api.field_test_runtime,
        "predict",
        lambda *_args, **_kwargs: JointPrediction("accepted", "rice", "rice_blast", "high", True, 0.9),
    )
    monkeypatch.setattr(api.field_test_logger, "record", lambda **_kwargs: None)
    monkeypatch.setattr(api.legacy_joint_override_audit_logger, "record", lambda **_kwargs: None)
    monkeypatch.setattr(
        "app.legacy_joint.field_test_override.settings.legacy_joint_field_test_override_permitted", True
    )
    api.legacy_joint_field_test_gate.activate("history-resilience")
    try:
        response = TestClient(app).post(
            "/disease/paddy/predict",
            files={"image": ("leaf.png", b"image", "image/png")},
            data={"crop_confirmed": "true", "crop_confirmation_token": "valid-for-test"},
        )
    finally:
        api.legacy_joint_field_test_gate.deactivate()

    assert response.status_code == 200
    assert response.json()["outcome"] == "accepted"
