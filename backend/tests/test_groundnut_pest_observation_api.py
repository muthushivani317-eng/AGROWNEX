from __future__ import annotations

import io
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.core.database import get_session
from app.groundnut_experimental import pest_observations
from app.groundnut_experimental.router import require_groundnut_controlled_tester, router


def _image() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (288, 288), (70, 120, 40)).save(stream, format="JPEG")
    return stream.getvalue()


class FakeSession:
    pass


class FakeStorage:
    def __init__(self) -> None:
        self.writes: list[dict] = []

    async def put(self, **kwargs):  # noqa: ANN003, ANN201
        self.writes.append(kwargs)
        return "private://stored"


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    user_id = uuid.uuid4()
    fake_session = FakeSession()
    storage = FakeStorage()
    saved = []

    async def session_override():  # noqa: ANN202
        yield fake_session

    async def owned_farm(_repo, farm_id, owner_id):  # noqa: ANN001, ANN202
        return SimpleNamespace(id=farm_id) if owner_id == user_id else None

    async def add_report(_repo, report):  # noqa: ANN001, ANN202
        report.id = uuid.uuid4()
        saved.append(report)
        return report

    monkeypatch.setattr(pest_observations, "get_private_storage", lambda: storage)
    monkeypatch.setattr(pest_observations.FarmRepository, "get_for_user", owned_farm)
    monkeypatch.setattr(pest_observations.DiseaseReportRepository, "add", add_report)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[require_groundnut_controlled_tester] = lambda: SimpleNamespace(
        user=SimpleNamespace(id=user_id), role="internal_tester"
    )
    return TestClient(app), user_id, storage, saved


def _submit(client: TestClient, **overrides):  # noqa: ANN003, ANN201
    data = {
        "damage_extent": "several",
        "spread_speed": "rapid",
        "consent": "true",
        "capture_method": "gallery",
        **overrides,
    }
    return client.post(
        "/api/v1/doctor/groundnut/pest-observations",
        data=data,
        files={"image": ("damage.jpg", _image(), "image/jpeg")},
    )


def test_pest_observation_stores_private_pending_evidence_without_diagnosis(api) -> None:  # noqa: ANN001
    client, user_id, storage, saved = api
    response = _submit(client)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending_expert_review"
    assert body["pest_label"] is None
    assert body["diagnosis"] is None
    assert len(storage.writes) == 1
    assert len(saved) == 1
    report = saved[0]
    assert report.user_id == user_id
    assert report.crop == "groundnut"
    assert report.disease is None and report.confidence is None and report.model_used is None
    assert report.image_url is None
    assert report.image_key.startswith(f"disease/groundnut-pest-observations/{user_id}/")
    assert report.review_consent is True
    assert report.review_status == "pending"
    assert report.needs_expert_review is True
    assert report.raw_response["farmer_reported"] == {
        "damage_extent": "several",
        "spread_speed": "rapid",
    }
    assert report.raw_response["diagnosis_assigned"] is False


def test_pest_observation_rejects_unowned_farm(api, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ANN001
    client, _user_id, storage, saved = api

    async def not_owned(_repo, _farm_id, _owner_id):  # noqa: ANN001, ANN202
        return None

    monkeypatch.setattr(pest_observations.FarmRepository, "get_for_user", not_owned)
    response = _submit(client, farm_id=str(uuid.uuid4()))
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "GROUNDNUT_FARM_NOT_FOUND"
    assert storage.writes == []
    assert saved == []


@pytest.mark.parametrize(
    ("field", "value"),
    [("damage_extent", "diagnosed_aphids"), ("spread_speed", "certain_pest")],
)
def test_pest_observation_rejects_invalid_farmer_inputs(api, field: str, value: str) -> None:  # noqa: ANN001
    client, _user_id, storage, saved = api
    response = _submit(client, **{field: value})
    assert response.status_code == 422
    assert storage.writes == []
    assert saved == []


def test_pest_observation_requires_review_consent(api) -> None:  # noqa: ANN001
    client, _user_id, storage, saved = api
    response = _submit(client, consent="false")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GROUNDNUT_PEST_REVIEW_CONSENT_REQUIRED"
    assert storage.writes == []
    assert saved == []
