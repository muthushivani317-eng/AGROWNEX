from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import httpx
import pytest
from app.modules.satellite.aoi import AoiValidationError, normalize_aoi
from app.modules.satellite.provider import CopernicusProvider

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[79.1, 10.7], [79.2, 10.7], [79.2, 10.8], [79.1, 10.8], [79.1, 10.7]]],
}


def test_aoi_normalizes_polygon_and_multipolygon() -> None:
    assert normalize_aoi(POLYGON)["type"] == "Polygon"
    multi = {"type": "MultiPolygon", "coordinates": [POLYGON["coordinates"]]}
    assert normalize_aoi(multi)["type"] == "MultiPolygon"


@pytest.mark.parametrize(
    "value",
    [
        {"type": "Point", "coordinates": [79, 10]},
        {"type": "Polygon", "coordinates": [[[79, 10], [80, 10], [80, 11]]]},
        {"type": "Polygon", "coordinates": [[[181, 10], [181, 11], [179, 11], [181, 10]]]},
        {"type": "Polygon", "coordinates": []},
    ],
)
def test_aoi_rejects_invalid_geometry(value: dict) -> None:
    with pytest.raises(AoiValidationError):
        normalize_aoi(value)


async def test_missing_credentials_fails_closed() -> None:
    outcome = await CopernicusProvider(client_id="", client_secret="").fetch_scene(
        POLYGON, capture_before=date(2026, 7, 12)
    )
    assert outcome.scene is None
    assert outcome.reason == "provider_not_configured"
    water = await CopernicusProvider(client_id="", client_secret="").fetch_water_evidence(
        POLYGON, capture_before=date(2026, 7, 12)
    )
    assert water.evidence is None
    assert water.reason == "provider_not_configured"


async def test_sentinel_one_discovery_never_fabricates_water_measurement() -> None:
    client = AsyncMock()
    client.post.return_value = httpx.Response(
        200,
        json={
            "features": [
                {"id": "S1-new", "properties": {"datetime": "2026-07-11T05:00:00Z"}},
                {"id": "S1-old", "properties": {"datetime": "2026-07-01T05:00:00Z"}},
            ]
        },
        request=httpx.Request("POST", "https://example.test"),
    )
    outcome = await CopernicusProvider(
        client_id="id", client_secret="secret", client=client
    ).fetch_water_evidence(POLYGON, capture_before=date(2026, 7, 12))
    assert outcome.evidence is not None
    assert outcome.evidence.scene_id == "S1-new"
    assert outcome.evidence.baseline_scene_id == "S1-old"
    assert outcome.evidence.surface_water_change is None
    assert outcome.evidence.policy_verified is False


async def test_timeout_and_rate_limit_are_stable() -> None:
    timeout_client = AsyncMock()
    timeout_client.post.side_effect = httpx.TimeoutException("timeout")
    timeout = CopernicusProvider(client_id="id", client_secret="secret", client=timeout_client)
    assert (
        await timeout.fetch_scene(POLYGON, capture_before=date(2026, 7, 12))
    ).reason == "provider_timeout"

    response = httpx.Response(429, request=httpx.Request("POST", "https://example.test"))
    limited_client = AsyncMock()
    limited_client.post.return_value = response
    limited = CopernicusProvider(client_id="id", client_secret="secret", client=limited_client)
    assert (
        await limited.fetch_scene(POLYGON, capture_before=date(2026, 7, 12))
    ).reason == "provider_rate_limited"


async def test_invalid_provider_response_fails_closed() -> None:
    response = httpx.Response(
        200, json={"unexpected": True}, request=httpx.Request("POST", "https://example.test")
    )
    client = AsyncMock()
    client.post.return_value = response
    provider = CopernicusProvider(client_id="id", client_secret="secret", client=client)
    outcome = await provider.fetch_scene(POLYGON, capture_before=date(2026, 7, 12))
    assert outcome.scene is None
    assert outcome.reason == "provider_error"


async def test_no_recent_scene_reports_acquisition_delay() -> None:
    client = AsyncMock()
    client.post.side_effect = [
        httpx.Response(
            200,
            json={"access_token": "token"},
            request=httpx.Request("POST", "https://example.test"),
        ),
        httpx.Response(
            200, json={"features": []}, request=httpx.Request("POST", "https://example.test")
        ),
    ]
    outcome = await CopernicusProvider(
        client_id="id", client_secret="secret", client=client
    ).fetch_scene(POLYGON, capture_before=date(2026, 7, 12))
    assert outcome.scene is None
    assert outcome.reason == "acquisition_delay"


async def test_real_contract_produces_provenance_bound_scene() -> None:
    stats = {
        "data": [
            {
                "outputs": {
                    "bands": {
                        "bands": {
                            "0": {"stats": {"mean": 0.06}},
                            "1": {"stats": {"mean": 0.15}},
                            "2": {"stats": {"mean": 0.30}},
                            "3": {"stats": {"mean": 0.45}},
                            "4": {"stats": {"mean": 0.25}},
                        }
                    }
                }
            }
        ]
    }
    client = AsyncMock()
    client.post.side_effect = [
        httpx.Response(
            200,
            json={"access_token": "token"},
            request=httpx.Request("POST", "https://example.test"),
        ),
        httpx.Response(
            200,
            json={
                "features": [
                    {
                        "id": "S2-scene",
                        "properties": {"datetime": "2026-07-11T05:00:00Z", "eo:cloud_cover": 7.0},
                    }
                ]
            },
            request=httpx.Request("POST", "https://example.test"),
        ),
        httpx.Response(200, json=stats, request=httpx.Request("POST", "https://example.test")),
    ]
    outcome = await CopernicusProvider(
        client_id="id", client_secret="secret", client=client
    ).fetch_scene(POLYGON, capture_before=date(2026, 7, 12))
    assert outcome.scene is not None
    assert outcome.scene.is_sample is False
    assert outcome.scene.bands and outcome.scene.bands.nir == 0.45
    assert outcome.scene.metadata["scene_id"] == "S2-scene"
    assert outcome.scene.metadata["processing_version"] == "cdse-statistics-v1"
