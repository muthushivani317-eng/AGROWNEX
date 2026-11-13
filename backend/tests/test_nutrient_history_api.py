from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.modules.auth.dependencies import get_auth_service, get_current_user
from app.modules.nutrient.dependencies import get_nutrient_service
from app.modules.nutrient.router import router


def _report(*, crop: str, confidence: int = 91):
    analysis = SimpleNamespace(
        primary_deficiency="nitrogen",
        secondary_deficiency="zinc",
        status="confirmed",
        confidence=confidence,
        severity="moderate",
        affected_area="widespread",
        disease_conflict=False,
        needs_test=False,
        needs_expert=False,
        soil_reference={"has_data": True, "macro_ratings": {"nitrogen": "low"}},
        satellite_reference=None,
        weather_reference=None,
        explanation_tamil="provider-specific claim",
        explanation_english="provider-specific claim",
    )
    remedy = SimpleNamespace(
        category="nutrient",
        code="nutrient.rec.nitrogen.deficiency",
        nutrient="nitrogen",
        severity="warning",
        priority="medium",
    )
    return SimpleNamespace(
        id=uuid4(),
        farm_id=uuid4(),
        crop=crop,
        image_url="private://leaf.jpg",
        thumbnail_url=None,
        capture_date=None,
        provider="gemini",
        model_used="vision",
        status="analyzed",
        language="en",
        latitude=None,
        longitude=None,
        weather_snapshot=None,
        analysis=analysis,
        symptoms=[SimpleNamespace(code="yellowing")],
        recommendations=[remedy],
        created_at=datetime.now(UTC),
    )


class _HistoryService:
    def __init__(self, reports):
        self.reports = reports

    async def list_reports(self, _user, _farm_id: UUID, *, page: int, page_size: int):
        return SimpleNamespace(
            items=self.reports,
            page=page,
            page_size=page_size,
            total=len(self.reports),
            total_pages=1 if self.reports else 0,
        )

    async def analyze(self, _user, _payload):
        return self.reports[0]

    async def latest(self, _user, _farm_id: UUID):
        return self.reports[0]

    async def get_report(self, _user, _report_id: UUID):
        return self.reports[0]


def _app(service: _HistoryService, *, authenticated: bool) -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    test_app.dependency_overrides[get_nutrient_service] = lambda: service
    if authenticated:
        test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    else:
        # get_current_user still requires its service dependency before it rejects
        # a missing bearer token; no real authentication backend is needed here.
        test_app.dependency_overrides[get_auth_service] = lambda: object()
    return test_app


@pytest.mark.asyncio
async def test_history_requires_authentication() -> None:
    app = _app(_HistoryService([]), authenticated=False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/nutrient/history", params={"farm_id": str(uuid4())}
        )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_history_response_schema_and_pagination_match_frontend_contract() -> None:
    reports = [_report(crop="Paddy", confidence=83)]
    app = _app(_HistoryService(reports), authenticated=True)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/nutrient/history",
            params={"farm_id": str(reports[0].farm_id), "page": 1, "page_size": 20},
        )

    assert response.status_code == 200
    page = response.json()["data"]
    assert {"items", "page", "page_size", "total", "total_pages"} <= page.keys()
    assert page["total"] == 1
    item = page["items"][0]
    assert item["id"] == str(reports[0].id)
    assert item["crop"] == "Paddy"
    assert item["analysis"]["confidence"] == 83
    assert item["recommendations"][0]["category"] == "nutrient"


@pytest.mark.asyncio
async def test_groundnut_history_uses_report_safety_sanitization() -> None:
    reports = [_report(crop="Groundnut")]
    app = _app(_HistoryService(reports), authenticated=True)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/nutrient/history", params={"farm_id": str(reports[0].farm_id)}
        )

    assert response.status_code == 200
    item = response.json()["data"]["items"][0]
    analysis = item["analysis"]
    assert analysis["status"] == "possible"
    assert analysis["confidence"] is None
    assert analysis["confidence_band"] is None
    assert analysis["needs_test"] is True
    assert analysis["needs_expert"] is True
    assert analysis["expert_verified"] is False
    assert analysis["suggested_next_evidence"] == ["soil_or_tissue_test", "expert_review"]
    assert analysis["explanation_english"] is None
    assert analysis["explanation_tamil"] is None
    assert [rec["category"] for rec in item["recommendations"]] == ["test", "expert"]
    assert all(rec["nutrient"] is None for rec in item["recommendations"])


@pytest.mark.asyncio
async def test_groundnut_confidence_is_suppressed_on_all_report_endpoints() -> None:
    report = _report(crop="Groundnut")
    app = _app(_HistoryService([report]), authenticated=True)
    requests = [
        ("post", "/api/v1/nutrient/analyze", {
            "json": {
                "image_base64": "0123456789abcdef",
                "mime_type": "image/jpeg",
                "farm_id": str(report.farm_id),
                "crop": "Groundnut",
            }
        }),
        ("get", "/api/v1/nutrient/latest", {"params": {"farm_id": str(report.farm_id)}}),
        ("get", f"/api/v1/nutrient/report/{report.id}", {}),
    ]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for method, url, kwargs in requests:
            response = await getattr(client, method)(url, **kwargs)
            assert response.status_code in {200, 201}
            analysis = response.json()["data"]["analysis"]
            assert analysis["confidence"] is None
            assert analysis["confidence_band"] is None
            assert analysis["explanation_english"] is None
            assert analysis["explanation_tamil"] is None

        recommendations = await client.get(
            "/api/v1/nutrient/recommendations",
            params={"farm_id": str(report.farm_id)},
        )
    assert recommendations.status_code == 200
    assert [item["category"] for item in recommendations.json()["data"]] == ["test", "expert"]
