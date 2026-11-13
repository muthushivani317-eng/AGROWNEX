from __future__ import annotations

import io
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.groundnut_experimental.router import (
    require_groundnut_controlled_tester,
    router,
)
from app.groundnut_experimental.service import (
    GroundnutModelUnavailableError,
    get_groundnut_prediction_service,
)
from app.groundnut_experimental.stt import (
    GroundnutSpeechError,
    GroundnutSpeechService,
    get_groundnut_speech_service,
)


class FakeService:
    def __init__(self, result: dict[str, Any] | None = None, error: Exception | None = None):
        self.result = result
        self.error = error

    def predict(self, _image: Image.Image) -> dict[str, Any]:
        if self.error:
            raise self.error
        assert self.result is not None
        return self.result


class FakeSpeechService:
    def __init__(self, transcript: str = "dark leaf spots", error: GroundnutSpeechError | None = None):
        self.transcript = transcript
        self.error = error
        self.calls: list[tuple[bytes, str, str]] = []

    async def transcribe(self, audio: bytes, *, content_type: str, language: str) -> str:
        self.calls.append((audio, content_type, language))
        if self.error:
            raise self.error
        return self.transcript


def ranked(class_id: str, display_name: str, confidence: float) -> dict[str, Any]:
    return {
        "class_id": class_id,
        "display_name": display_name,
        "confidence": confidence,
    }


def result(*, status: str = "accepted", category: str | None = "HIGH") -> dict[str, Any]:
    top = ranked("rust", "Rust", 0.96)
    accepted = status == "accepted"
    quality_ok = status != "rejected"
    return {
        "status": status,
        "confidence_category": category,
        "prediction": top if accepted else None,
        "candidate_prediction": top if quality_ok else None,
        "top_predictions": (
            [
                top,
                ranked("early_leaf_spot", "Early Leaf Spot", 0.02),
                ranked("healthy_leaf", "Healthy Leaf", 0.01),
            ]
            if quality_ok
            else []
        ),
        "quality": {
            "accepted": quality_ok,
            "reasons": [] if quality_ok else ["IMAGE_TOO_DARK"],
            "width": 288,
            "height": 288,
            "brightness": 92.0,
            "contrast": 31.0,
            "blur_score": 42.0,
        },
        "rejection_reasons": ([] if accepted else (["IMAGE_TOO_DARK"] if not quality_ok else ["EXPERT_REVIEW_REQUIRED"])),
        "expert_review_required": status == "review_required",
        "model_id": "groundnut-efficientnet-b2-v1",
        "device": "cpu",
    }


def image_bytes(size: tuple[int, int] = (288, 288), fmt: str = "JPEG") -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", size, (50, 130, 60)).save(stream, format=fmt)
    return stream.getvalue()


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setattr(settings, "groundnut_experimental_enabled", True)
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    test_app.dependency_overrides[require_groundnut_controlled_tester] = lambda: object()
    return test_app


def set_service(app: FastAPI, service: FakeService) -> None:
    app.dependency_overrides[get_groundnut_prediction_service] = lambda: service


def upload(client: TestClient, payload: bytes | None = None, content_type: str = "image/jpeg"):
    return client.post(
        "/api/v1/doctor/groundnut/predict",
        files={"image": ("leaf.jpg", payload or image_bytes(), content_type)},
    )


def test_text_symptoms_return_preliminary_guidance_without_model_confidence(app: FastAPI) -> None:
    response = TestClient(app).post(
        "/api/v1/doctor/groundnut/symptoms",
        json={"symptoms": ["dark_leaf_spots", "yellow_halo_around_spots"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "preliminary_guidance"
    assert body["possible_patterns"] == ["leaf_spot_pattern"]
    assert body["expert_review_required"] is True
    assert body["confirmed_disease"] is None
    assert body["image_model_confidence"] is None
    assert "not a diagnosis" in body["warnings"][1]


def test_text_symptoms_reject_unknown_vocabulary(app: FastAPI) -> None:
    response = TestClient(app).post(
        "/api/v1/doctor/groundnut/symptoms",
        json={"symptoms": ["definitely_rust"]},
    )
    assert response.status_code == 422


def test_text_symptoms_require_at_least_one_observation(app: FastAPI) -> None:
    response = TestClient(app).post(
        "/api/v1/doctor/groundnut/symptoms",
        json={"symptoms": []},
    )
    assert response.status_code == 422


def test_text_symptoms_require_authentication() -> None:
    protected_app = FastAPI()
    protected_app.include_router(router, prefix="/api/v1")
    response = TestClient(protected_app).post(
        "/api/v1/doctor/groundnut/symptoms",
        json={"symptoms": ["dark_leaf_spots"]},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.parametrize("language", ["en-IN", "ta-IN", "ml-IN"])
def test_transcription_accepts_supported_languages(app: FastAPI, language: str) -> None:
    speech = FakeSpeechService(transcript="visible leaf symptoms")
    app.dependency_overrides[get_groundnut_speech_service] = lambda: speech
    response = TestClient(app).post(
        "/api/v1/doctor/groundnut/transcribe",
        data={"language": language},
        files={"audio": ("symptoms.wav", b"RIFF-safe-test-audio", "audio/wav")},
    )
    assert response.status_code == 200
    assert response.json() == {"transcript": "visible leaf symptoms"}
    assert speech.calls == [(b"RIFF-safe-test-audio", "audio/wav", language)]


def test_transcription_rejects_unsupported_language_and_audio(app: FastAPI) -> None:
    speech = FakeSpeechService()
    app.dependency_overrides[get_groundnut_speech_service] = lambda: speech
    client = TestClient(app)
    bad_language = client.post(
        "/api/v1/doctor/groundnut/transcribe",
        data={"language": "hi-IN"},
        files={"audio": ("symptoms.wav", b"RIFF", "audio/wav")},
    )
    assert bad_language.status_code == 422
    bad_type = client.post(
        "/api/v1/doctor/groundnut/transcribe",
        data={"language": "ta-IN"},
        files={"audio": ("symptoms.txt", b"words", "text/plain")},
    )
    assert bad_type.status_code == 415
    assert speech.calls == []


def test_transcription_returns_safe_unconfigured_error(app: FastAPI) -> None:
    speech = FakeSpeechService(error=GroundnutSpeechError("GROUNDNUT_STT_UNCONFIGURED"))
    app.dependency_overrides[get_groundnut_speech_service] = lambda: speech
    response = TestClient(app).post(
        "/api/v1/doctor/groundnut/transcribe",
        data={"language": "ml-IN"},
        files={"audio": ("symptoms.wav", b"RIFF", "audio/wav")},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": {"code": "GROUNDNUT_STT_UNCONFIGURED"}}


def test_stt_service_fails_closed_without_server_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "groundnut_stt_enabled", True)
    monkeypatch.setattr(settings, "google_cloud_stt_credentials_json", "")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    with pytest.raises(GroundnutSpeechError, match="GROUNDNUT_STT_UNCONFIGURED"):
        GroundnutSpeechService()._credentials()


def test_authenticated_transcript_mapping_returns_observations_only(app: FastAPI) -> None:
    response = TestClient(app).post(
        "/api/v1/doctor/groundnut/symptoms/map-transcript",
        json={
            "language": "en-IN",
            "transcript": "Dark leaf spots. It may be a disease.",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "matched_symptoms": ["dark_leaf_spots"],
        "unmatched_text": ["It may be a disease"],
        "ambiguous_text": [],
    }


def test_successful_upload_returns_valid_experimental_prediction(app: FastAPI) -> None:
    set_service(app, FakeService(result()))
    response = upload(TestClient(app))
    assert response.status_code == 200
    body = response.json()
    assert body["crop"] == "groundnut"
    assert body["model_version"] == "groundnut-efficientnet-b2-v1"
    assert body["experimental"] is True
    assert "70.22%" in body["experimental_notice"]
    assert body["status"] == "accepted"
    assert body["predicted_disease"]["class_id"] == "rust"
    assert body["confidence_category"] == "HIGH"
    assert body["confidence_score"] == pytest.approx(0.96)
    assert len(body["top_three_predictions"]) == 3
    assert body["expert_review_required"] is False


def test_invalid_file_type_is_rejected_before_inference(app: FastAPI) -> None:
    set_service(app, FakeService(result()))
    response = upload(TestClient(app), b"GIF89a", "image/gif")
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "GROUNDNUT_IMAGE_FORMAT_UNSUPPORTED"


def test_corrupted_image_is_rejected(app: FastAPI) -> None:
    set_service(app, FakeService(result()))
    response = upload(TestClient(app), b"not-an-image")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GROUNDNUT_IMAGE_CORRUPTED"


def test_oversized_upload_is_rejected(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "groundnut_max_upload_bytes", 10)
    set_service(app, FakeService(result()))
    response = upload(TestClient(app), b"x" * 11)
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "GROUNDNUT_IMAGE_TOO_LARGE"


def test_minimum_dimensions_are_enforced(app: FastAPI) -> None:
    set_service(app, FakeService(result()))
    response = upload(TestClient(app), image_bytes((100, 100)))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GROUNDNUT_IMAGE_TOO_SMALL"


def test_low_quality_result_contains_no_diagnosis(app: FastAPI) -> None:
    set_service(app, FakeService(result(status="rejected", category=None)))
    response = upload(TestClient(app))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["predicted_disease"] is None
    assert body["candidate_prediction"] is None
    assert body["image_quality"]["status"] == "rejected"
    assert body["rejection_reasons"] == ["IMAGE_TOO_DARK"]


@pytest.mark.parametrize("category", ["MEDIUM", "LOW"])
def test_uncertain_result_is_candidate_only_and_requires_review(app: FastAPI, category: str) -> None:
    set_service(app, FakeService(result(status="review_required", category=category)))
    response = upload(TestClient(app))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "review_required"
    assert body["predicted_disease"] is None
    assert body["candidate_prediction"]["class_id"] == "rust"
    assert body["confidence_category"] == category
    assert body["expert_review_required"] is True


def test_model_loading_failure_returns_service_unavailable(app: FastAPI) -> None:
    set_service(
        app,
        FakeService(error=GroundnutModelUnavailableError("GROUNDNUT_MODEL_LOAD_FAILED")),
    )
    response = upload(TestClient(app))
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "GROUNDNUT_MODEL_LOAD_FAILED"
