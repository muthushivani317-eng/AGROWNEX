from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.banana_v3 import api_router as api
from app.banana_v3.api_router import require_banana_controlled_tester, router
from app.banana_v3.schemas import DiseaseBlock, GateBlock, PredictionResponse, ResultBlock
from app.core.database import get_session


def _response() -> PredictionResponse:
    return PredictionResponse(
        request_id=uuid4(),
        status="accepted",
        decision_code="BV3_ACCEPTED",
        result=ResultBlock(class_id="black_sigatoka", confidence=0.9, margin=0.8),
        healthy_gate=GateBlock(predicted_class="disease", confidence=0.9, margin=0.8, accepted=True),
        disease_classifier=DiseaseBlock(
            predicted_class="black_sigatoka", confidence=0.9, margin=0.8, accepted=True, executed=True
        ),
        message_key="banana.result.accepted",
        requires_follow_up_photo=False,
        requires_human_review=False,
        runtime_backend="onnx",
        processing_time_ms=1,
        timestamp_utc=datetime.now(UTC),
    )


def test_prediction_is_returned_when_history_persistence_fails(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_banana_controlled_tester] = lambda: SimpleNamespace(
        user=SimpleNamespace(id="tester"), role="internal_tester"
    )

    async def session_override():
        yield object()

    app.dependency_overrides[get_session] = session_override

    async def persistence_failure(*_args, **_kwargs):
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(api, "persist_controlled_test_report", persistence_failure)
    monkeypatch.setattr(api.confirmation_store, "validate", lambda **_kwargs: None)
    monkeypatch.setattr(api, "load_image", lambda _payload: object())
    monkeypatch.setattr(api, "require_safe_image", lambda _image: None)
    monkeypatch.setattr(api._service, "predict", lambda _payload: _response())
    monkeypatch.setattr(api.field_test_logger, "record", lambda **_kwargs: None)

    response = TestClient(app).post(
        "/disease/banana/predict",
        files={"image": ("leaf.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        data={"crop_confirmation_token": "valid-for-test"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
