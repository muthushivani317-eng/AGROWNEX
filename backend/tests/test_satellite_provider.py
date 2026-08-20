from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import httpx
import pytest
from app.modules.disease.storage import MockStorage, UnavailableStorage
from app.modules.satellite.aoi import AoiValidationError, normalize_aoi
from app.modules.satellite.engine import BandReflectance, compute_indices
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


def _water_stats(mean: float, *, samples: int = 100, no_data: int = 10) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "data": [
                {
                    "outputs": {
                        "water": {
                            "bands": {
                                "B0": {
                                    "stats": {
                                        "mean": mean,
                                        "sampleCount": samples,
                                        "noDataCount": no_data,
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        },
        request=httpx.Request("POST", "https://example.test"),
    )


async def test_sentinel_one_comparison_returns_real_screening_evidence() -> None:
    client = AsyncMock()
    client.post.side_effect = [
        _token_response(),
        httpx.Response(
            200,
            json={
                "features": [
                    {
                        "id": "S1-new",
                        "properties": {
                            "datetime": "2026-07-11T05:00:00Z",
                            "sat:relative_orbit": 42,
                        },
                    },
                    {
                        "id": "S1-old",
                        "properties": {
                            "datetime": "2026-07-01T05:00:00Z",
                            "sat:relative_orbit": 42,
                        },
                    },
                ]
            },
            request=httpx.Request("POST", "https://example.test"),
        ),
        _water_stats(0.14),
        _water_stats(0.04),
    ]
    outcome = await CopernicusProvider(
        client_id="id", client_secret="secret", client=client
    ).fetch_water_evidence(POLYGON, capture_before=date(2026, 7, 12))
    assert outcome.evidence is not None
    assert outcome.evidence.scene_id == "S1-new"
    assert outcome.evidence.baseline_scene_id == "S1-old"
    assert outcome.evidence.surface_water_change == "increase"
    assert outcome.evidence.coverage_pct == 90.0
    assert outcome.evidence.quality_usable is True
    assert outcome.evidence.policy_verified is False


def test_water_statistics_request_uses_real_sar_bands_and_terrain_correction() -> None:
    request = CopernicusProvider._water_statistics_request(POLYGON, "2026-07-11T05:00:00Z")
    data = request["input"]["data"][0]
    assert data["type"] == "sentinel-1-grd"
    assert data["processing"]["orthorectify"] is True
    assert data["processing"]["backCoeff"] == "GAMMA0_TERRAIN"
    assert 'bands:["VV","VH","dataMask"]' in request["aggregation"]["evalscript"]


async def test_sentinel_one_low_coverage_fails_closed() -> None:
    client = AsyncMock()
    client.post.side_effect = [
        _token_response(),
        httpx.Response(
            200,
            json={
                "features": [
                    {"id": "new", "properties": {"datetime": "2026-07-11T05:00:00Z"}},
                    {"id": "old", "properties": {"datetime": "2026-07-01T05:00:00Z"}},
                ]
            },
            request=httpx.Request("POST", "https://example.test"),
        ),
        _water_stats(0.2, samples=100, no_data=60),
        _water_stats(0.0, samples=100, no_data=60),
    ]
    outcome = await CopernicusProvider(
        client_id="id", client_secret="secret", client=client
    ).fetch_water_evidence(POLYGON, capture_before=date(2026, 7, 12))
    assert outcome.evidence is not None
    assert outcome.evidence.quality_usable is False
    assert "usable_coverage" in outcome.evidence.evidence_missing


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
                            "B0": {"stats": {"mean": 0.06}},
                            "B1": {"stats": {"mean": 0.15}},
                            "B2": {"stats": {"mean": 0.30}},
                            "B3": {"stats": {"mean": 0.45}},
                            "B4": {"stats": {"mean": 0.25}},
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


def test_statistics_request_uses_wgs84_resolution_and_data_mask() -> None:
    request = CopernicusProvider._statistics_request(POLYGON, date(2026, 7, 11))

    assert request["aggregation"]["timeRange"] == {
        "from": "2026-07-11T00:00:00Z",
        "to": "2026-07-12T00:00:00Z",
    }
    assert request["aggregation"]["aggregationInterval"] == {"of": "P1D"}
    assert request["input"]["bounds"]["properties"]["crs"].endswith("/4326")
    assert request["aggregation"]["resx"] == pytest.approx(0.0001)
    assert request["aggregation"]["resy"] == pytest.approx(0.0001)
    assert 'id:"dataMask"' in request["aggregation"]["evalscript"]
    assert "dataMask:[v?1:0]" in request["aggregation"]["evalscript"]


def _stats_response(*, nir: float = 0.45, swir: float = 0.25) -> httpx.Response:
    stats = {
        "data": [
            {
                "outputs": {
                    "bands": {
                        "bands": {
                            "B0": {"stats": {"mean": 0.06}},
                            "B1": {"stats": {"mean": 0.15}},
                            "B2": {"stats": {"mean": 0.30}},
                            "B3": {"stats": {"mean": nir}},
                            "B4": {"stats": {"mean": swir}},
                        }
                    }
                }
            }
        ]
    }
    return httpx.Response(200, json=stats, request=httpx.Request("POST", "https://example.test"))


def _scene_search_response() -> httpx.Response:
    return httpx.Response(
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
    )


def _token_response() -> httpx.Response:
    return httpx.Response(
        200, json={"access_token": "token"}, request=httpx.Request("POST", "https://example.test")
    )


async def test_available_scene_returns_numeric_data_before_image_rendering() -> None:
    client = AsyncMock()
    client.post.side_effect = [
        _token_response(),
        _scene_search_response(),
        _stats_response(),
    ]
    provider = CopernicusProvider(
        client_id="id", client_secret="secret", client=client, storage=MockStorage()
    )
    outcome = await provider.fetch_scene(POLYGON, capture_before=date(2026, 7, 12))
    assert outcome.scene is not None
    assert outcome.scene.images == {}
    assert outcome.scene.thumbnail_url is None
    assert outcome.scene.bands and outcome.scene.bands.nir == 0.45
    # One best-effort sub-AOI request follows the field-wide statistics call;
    # this fixture intentionally provides no sub-zone response.
    assert client.post.await_count == 4


async def test_real_sub_aoi_variation_creates_sampling_zone_metadata() -> None:
    client = AsyncMock()
    client.post.side_effect = [
        _stats_response(nir=0.20, swir=0.35),
        _stats_response(),
        _stats_response(),
        _stats_response(),
    ]
    provider = CopernicusProvider(client_id="id", client_secret="secret", client=client)
    field_indices = compute_indices(
        BandReflectance(blue=0.06, red=0.15, red_edge=0.30, nir=0.45, swir=0.25)
    )

    zones = await provider._fetch_spatial_zones("token", POLYGON, date(2026, 7, 11), field_indices)

    assert zones
    assert zones[0]["zone_id"] == "sat-zone-1"
    assert zones[0]["observation_class"] == "poor_performing"
    assert zones[0]["quality"] == "usable"


async def test_background_render_stores_true_color_and_ndvi_images() -> None:
    client = AsyncMock()
    client.post.side_effect = [
        _token_response(),
        httpx.Response(200, content=b"PNGDATA-truecolor", request=httpx.Request("POST", "x")),
        httpx.Response(200, content=b"PNGDATA-ndvi", request=httpx.Request("POST", "x")),
    ]
    provider = CopernicusProvider(
        client_id="id", client_secret="secret", client=client, storage=MockStorage()
    )
    images, thumbnail = await provider.render_scene_images(
        POLYGON, capture_date=date(2026, 7, 11), scene_id="S2-scene"
    )
    assert images == {
        "true_color": "https://r2.mock.local/satellite/S2-scene/true_color.png",
        "ndvi": "https://r2.mock.local/satellite/S2-scene/ndvi.png",
    }
    assert thumbnail == "https://r2.mock.local/satellite/S2-scene/true_color.png"


async def test_image_storage_failure_never_blocks_the_numeric_scene() -> None:
    """R2 not being configured (or a render/upload failure) must degrade to no
    pictures, never to a failed refresh -- the indices are the source of truth."""
    client = AsyncMock()
    client.post.side_effect = [
        _token_response(),
        httpx.Response(200, content=b"PNGDATA-truecolor", request=httpx.Request("POST", "x")),
        httpx.Response(200, content=b"PNGDATA-ndvi", request=httpx.Request("POST", "x")),
    ]
    images, thumbnail = await CopernicusProvider(
        client_id="id", client_secret="secret", client=client, storage=UnavailableStorage()
    ).render_scene_images(POLYGON, capture_date=date(2026, 7, 11), scene_id="S2-scene")
    assert images == {}
    assert thumbnail is None


async def test_image_render_http_failure_never_blocks_the_numeric_scene() -> None:
    client = AsyncMock()
    client.post.side_effect = [
        _token_response(),
        httpx.Response(500, request=httpx.Request("POST", "x")),
        httpx.Response(500, request=httpx.Request("POST", "x")),
    ]
    images, thumbnail = await CopernicusProvider(
        client_id="id", client_secret="secret", client=client, storage=MockStorage()
    ).render_scene_images(POLYGON, capture_date=date(2026, 7, 11), scene_id="S2-scene")
    assert images == {}
    assert thumbnail is None
