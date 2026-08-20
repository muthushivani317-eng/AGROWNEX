from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

import httpx

from app.core.logging import get_logger
from app.modules.disease.storage import ObjectStorage, get_default_storage
from app.modules.satellite.constants import (
    ACQUISITION_LOOKBACK_DAYS,
    CLOUD_USABLE_MAX,
    NDVI_BARE,
    NDVI_GOOD,
    NDVI_LOW,
    NDVI_MODERATE,
    NDVI_VERY_LOW,
    RENDERED_IMAGE_SIZE_PX,
    SATELLITE_IMAGE_PREFIX,
    SATELLITE_PROVIDER,
    SatelliteProviderName,
    UnavailableReason,
)
from app.modules.satellite.engine import BandReflectance, IndexValues
from app.modules.satellite.waterlogging import WaterloggingEvidence

logger = get_logger("satellite.provider")

# Standard Sentinel-2 "true colour" render (the well-known 2.5x-gain RGB
# combination used across Sentinel Hub's public custom-script gallery) --
# not a fabricated visualization, just the display-corrected version of the
# same B02/B03/B04 bands the app already reads.
_TRUE_COLOR_EVALSCRIPT = """
//VERSION=3
function setup() {
  return { input: [{ bands: ["B02", "B03", "B04", "dataMask"] }], output: { bands: 4 } };
}
function evaluatePixel(s) {
  return [2.5 * s.B04, 2.5 * s.B03, 2.5 * s.B02, s.dataMask];
}
"""

# NDVI rendered as a colour map using the EXACT same six health thresholds the
# numeric dashboard badge already uses (NDVI_BARE/VERY_LOW/LOW/MODERATE/GOOD in
# constants.py) -- so the picture a farmer sees can never disagree with the
# health label shown next to it.
_NDVI_COLOR_EVALSCRIPT = f"""
//VERSION=3
function setup() {{
  return {{ input: [{{ bands: ["B04", "B08", "dataMask"] }}], output: {{ bands: 4 }} }};
}}
function evaluatePixel(s) {{
  if (s.dataMask === 0) return [0, 0, 0, 0];
  var ndvi = (s.B08 - s.B04) / (s.B08 + s.B04 + 0.000001);
  var r, g, b;
  if (ndvi < {NDVI_BARE}) {{ r = 0.60; g = 0.40; b = 0.20; }}
  else if (ndvi < {NDVI_VERY_LOW}) {{ r = 0.85; g = 0.70; b = 0.30; }}
  else if (ndvi < {NDVI_LOW}) {{ r = 0.95; g = 0.85; b = 0.20; }}
  else if (ndvi < {NDVI_MODERATE}) {{ r = 0.75; g = 0.85; b = 0.15; }}
  else if (ndvi < {NDVI_GOOD}) {{ r = 0.35; g = 0.70; b = 0.15; }}
  else {{ r = 0.05; g = 0.45; b = 0.10; }}
  return [r, g, b, s.dataMask];
}}
"""


@dataclass(frozen=True)
class ProviderScene:
    capture_date: date
    provider: str
    cloud_cover: float
    resolution_m: float
    bands: BandReflectance | None = None
    indices: IndexValues | None = None
    index_stats: dict[str, tuple[float, float, float, float]] = field(default_factory=dict)
    images: dict[str, str] = field(default_factory=dict)
    thumbnail_url: str | None = None
    is_sample: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FetchOutcome:
    scene: ProviderScene | None
    reason: str = UnavailableReason.NONE.value


@dataclass(frozen=True)
class WaterEvidenceOutcome:
    evidence: WaterloggingEvidence | None
    reason: str = UnavailableReason.NONE.value


class SatelliteProvider(Protocol):
    name: str

    async def fetch_scene(self, polygon: dict, *, capture_before: date) -> FetchOutcome: ...

    async def fetch_water_evidence(
        self, polygon: dict, *, capture_before: date
    ) -> WaterEvidenceOutcome: ...

    async def render_scene_images(
        self, polygon: dict, *, capture_date: date, scene_id: str
    ) -> tuple[dict[str, str], str | None]: ...


class CopernicusProvider:
    name = SatelliteProviderName.COPERNICUS.value
    TOKEN_URL = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    STAC_URL = "https://stac.dataspace.copernicus.eu/v1/search"
    STATISTICS_URL = "https://sh.dataspace.copernicus.eu/api/v1/statistics"
    PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: float = 30.0,
        client: Any | None = None,
        storage: ObjectStorage | None = None,
    ) -> None:
        self.client_id = (
            client_id if client_id is not None else os.getenv("COPERNICUS_CLIENT_ID", "")
        )
        self.client_secret = (
            client_secret
            if client_secret is not None
            else os.getenv("COPERNICUS_CLIENT_SECRET", "")
        )
        self.timeout = timeout
        self._client = client
        self.storage = storage or get_default_storage()

    async def _post(self, url: str, **kwargs: Any) -> httpx.Response:
        if self._client is not None:
            return await self._client.post(url, **kwargs)
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            return await client.post(url, **kwargs)

    async def _access_token(self) -> tuple[str | None, str]:
        if not self.client_id or not self.client_secret:
            return None, UnavailableReason.PROVIDER_NOT_CONFIGURED.value
        token_response = await self._post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=self.timeout,
        )
        if reason := self._failure(token_response):
            return None, reason
        token = token_response.json().get("access_token")
        if not isinstance(token, str) or not token:
            return None, UnavailableReason.PROVIDER_ERROR.value
        return token, UnavailableReason.NONE.value

    @staticmethod
    def _failure(response: httpx.Response) -> str | None:
        if response.status_code == 429:
            return UnavailableReason.PROVIDER_RATE_LIMITED.value
        if response.status_code >= 400:
            return UnavailableReason.PROVIDER_ERROR.value
        return None

    async def fetch_scene(self, polygon: dict, *, capture_before: date) -> FetchOutcome:
        if not self.client_id or not self.client_secret:
            return FetchOutcome(None, UnavailableReason.PROVIDER_NOT_CONFIGURED.value)
        try:
            token, reason = await self._access_token()
            if token is None:
                return FetchOutcome(None, reason)
            start = capture_before - timedelta(days=ACQUISITION_LOOKBACK_DAYS)
            search_response = await self._post(
                self.STAC_URL,
                json={
                    "collections": ["sentinel-2-l2a"],
                    "intersects": polygon,
                    "datetime": (
                        f"{start.isoformat()}T00:00:00Z/" f"{capture_before.isoformat()}T23:59:59Z"
                    ),
                    "query": {"eo:cloud_cover": {"lte": CLOUD_USABLE_MAX}},
                    "sortby": [{"field": "properties.datetime", "direction": "desc"}],
                    "limit": 1,
                },
                timeout=self.timeout,
            )
            if reason := self._failure(search_response):
                return FetchOutcome(None, reason)
            features = search_response.json().get("features")
            if not isinstance(features, list):
                return FetchOutcome(None, UnavailableReason.PROVIDER_ERROR.value)
            if not features:
                return FetchOutcome(None, UnavailableReason.ACQUISITION_DELAY.value)
            item = features[0]
            properties = item.get("properties", {})
            scene_id, captured, cloud = (
                item.get("id"),
                properties.get("datetime"),
                properties.get("eo:cloud_cover"),
            )
            if (
                not isinstance(scene_id, str)
                or not isinstance(captured, str)
                or isinstance(cloud, bool)
                or not isinstance(cloud, int | float)
            ):
                return FetchOutcome(None, UnavailableReason.PROVIDER_ERROR.value)
            capture_date = (
                datetime.fromisoformat(captured.replace("Z", "+00:00")).astimezone(UTC).date()
            )
            stats_response = await self._post(
                self.STATISTICS_URL,
                headers={"Authorization": f"Bearer {token}"},
                json=self._statistics_request(polygon, capture_date),
                timeout=self.timeout,
            )
            if reason := self._failure(stats_response):
                return FetchOutcome(None, reason)
            bands = self._parse_band_means(stats_response.json())
            if bands is None:
                return FetchOutcome(None, UnavailableReason.PROCESSING_ERROR.value)
            return FetchOutcome(
                ProviderScene(
                    capture_date=capture_date,
                    provider=self.name,
                    cloud_cover=float(cloud),
                    resolution_m=10.0,
                    bands=bands,
                    metadata={
                        "scene_id": scene_id,
                        "collection": "sentinel-2-l2a",
                        "acquired_at": captured,
                        "processing_version": "cdse-statistics-v1",
                        "quality": "cloud_masked_l2a",
                    },
                )
            )
        except httpx.TimeoutException:
            return FetchOutcome(None, UnavailableReason.PROVIDER_TIMEOUT.value)
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            logger.warning("copernicus request failed", exc_info=True)
            return FetchOutcome(None, UnavailableReason.PROVIDER_ERROR.value)

    async def render_scene_images(
        self, polygon: dict, *, capture_date: date, scene_id: str
    ) -> tuple[dict[str, str], str | None]:
        """Best-effort image enrichment, deliberately separate from indices.

        The refresh request only waits for scene discovery and statistics. Image
        rendering and object-storage uploads happen after that numeric session is
        committed, so a slow Process API or storage provider cannot hide NDVI.
        """
        try:
            token, reason = await self._access_token()
            if token is None:
                logger.warning("satellite background image auth unavailable: %s", reason)
                return {}, None
            return await self._fetch_and_store_images(token, polygon, capture_date, scene_id)
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            logger.warning("satellite background image rendering failed", exc_info=True)
            return {}, None

    @staticmethod
    def _statistics_request(polygon: dict, capture_date: date) -> dict[str, Any]:
        evalscript = (
            "//VERSION=3\nfunction setup(){return {input:[{bands:"
            '["B02","B04","B05","B08","B11","SCL","dataMask"]}],'
            'output:[{id:"bands",bands:5,sampleType:"FLOAT32"}]};}\n'
            "function evaluatePixel(s){let v=s.dataMask&&"
            "![1,3,7,8,9,10].includes(s.SCL);return {bands:v?"
            "[s.B02,s.B04,s.B05,s.B08,s.B11]:[NaN,NaN,NaN,NaN,NaN]};}"
        )
        period = {
            "from": f"{capture_date.isoformat()}T00:00:00Z",
            "to": f"{capture_date.isoformat()}T23:59:59Z",
        }
        return {
            "input": {
                "bounds": {"geometry": polygon},
                "data": [{"type": "sentinel-2-l2a", "dataFilter": {"timeRange": period}}],
            },
            "aggregation": {
                "timeRange": period,
                "aggregationInterval": {"of": "P1D"},
                "resx": 10,
                "resy": 10,
                "evalscript": evalscript,
            },
        }

    @staticmethod
    def _process_request(polygon: dict, capture_date: date, evalscript: str) -> dict[str, Any]:
        period = {
            "from": f"{capture_date.isoformat()}T00:00:00Z",
            "to": f"{capture_date.isoformat()}T23:59:59Z",
        }
        return {
            "input": {
                "bounds": {"geometry": polygon},
                "data": [{"type": "sentinel-2-l2a", "dataFilter": {"timeRange": period}}],
            },
            "output": {
                "width": RENDERED_IMAGE_SIZE_PX,
                "height": RENDERED_IMAGE_SIZE_PX,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
            },
            "evalscript": evalscript,
        }

    async def _fetch_rendered_image(
        self, token: str, polygon: dict, capture_date: date, evalscript: str
    ) -> bytes | None:
        """Render one PNG layer via the Process API. Best-effort: a failure here
        never blocks the numeric pipeline -- it just means no picture this pass,
        same honest-degradation pattern as the rest of the app's image storage."""
        try:
            response = await self._post(
                self.PROCESS_URL,
                headers={"Authorization": f"Bearer {token}"},
                json=self._process_request(polygon, capture_date, evalscript),
                timeout=self.timeout,
            )
            if response.status_code != 200:
                logger.warning("satellite image render failed: status=%s", response.status_code)
                return None
            return response.content
        except httpx.HTTPError:
            logger.warning("satellite image render request failed", exc_info=True)
            return None

    async def _fetch_and_store_images(
        self, token: str, polygon: dict, capture_date: date, scene_id: str
    ) -> tuple[dict[str, str], str | None]:
        """True-colour + NDVI-colour renders, uploaded to object storage. Never
        raises: any render or storage failure just means fewer/no images for this
        scene, not a failed refresh -- the numeric indices remain the source of
        truth regardless of whether a picture could be produced."""
        images: dict[str, str] = {}
        thumbnail_url: str | None = None
        try:
            true_color = await self._fetch_rendered_image(
                token, polygon, capture_date, _TRUE_COLOR_EVALSCRIPT
            )
            if true_color:
                url = await self.storage.put(
                    key=f"{SATELLITE_IMAGE_PREFIX}/{scene_id}/true_color.png",
                    data=true_color,
                    content_type="image/png",
                )
                images["true_color"] = url
                thumbnail_url = url
            ndvi_image = await self._fetch_rendered_image(
                token, polygon, capture_date, _NDVI_COLOR_EVALSCRIPT
            )
            if ndvi_image:
                url = await self.storage.put(
                    key=f"{SATELLITE_IMAGE_PREFIX}/{scene_id}/ndvi.png",
                    data=ndvi_image,
                    content_type="image/png",
                )
                images["ndvi"] = url
                thumbnail_url = thumbnail_url or url
        except Exception:
            logger.warning(
                "satellite image rendering/storage failed; continuing without imagery",
                exc_info=True,
            )
        return images, thumbnail_url

    @staticmethod
    def _parse_band_means(payload: Any) -> BandReflectance | None:
        try:
            bands = payload["data"][0]["outputs"]["bands"]["bands"]
            values: list[float] = []
            for index in range(5):
                entry = bands[str(index)] if isinstance(bands, dict) else bands[index]
                value = entry["stats"]["mean"]
                if isinstance(value, bool) or not isinstance(value, int | float):
                    return None
                values.append(float(value))
            return BandReflectance(
                blue=values[0], red=values[1], red_edge=values[2], nir=values[3], swir=values[4]
            )
        except (KeyError, IndexError, TypeError):
            return None

    async def fetch_water_evidence(
        self, polygon: dict, *, capture_before: date
    ) -> WaterEvidenceOutcome:
        """Discover compatible Sentinel-1 scenes without inventing a water metric.

        Surface-water derivation stays disabled until a versioned, expert-reviewed
        policy is configured; discovery alone is evidence for review, not flooding.
        """
        if not self.client_id or not self.client_secret:
            return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_NOT_CONFIGURED.value)
        try:
            start = capture_before - timedelta(days=ACQUISITION_LOOKBACK_DAYS * 2)
            response = await self._post(
                self.STAC_URL,
                json={
                    "collections": ["sentinel-1-grd"],
                    "intersects": polygon,
                    "datetime": (
                        f"{start.isoformat()}T00:00:00Z/" f"{capture_before.isoformat()}T23:59:59Z"
                    ),
                    "sortby": [{"field": "properties.datetime", "direction": "desc"}],
                    "limit": 2,
                },
                timeout=self.timeout,
            )
            if reason := self._failure(response):
                return WaterEvidenceOutcome(None, reason)
            features = response.json().get("features")
            if not isinstance(features, list):
                return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_ERROR.value)
            if not features:
                return WaterEvidenceOutcome(None, UnavailableReason.NO_IMAGERY.value)
            current = features[0]
            scene_id = current.get("id")
            captured = current.get("properties", {}).get("datetime")
            if not isinstance(scene_id, str) or not isinstance(captured, str):
                return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_ERROR.value)
            baseline = features[1].get("id") if len(features) > 1 else None
            baseline_id = baseline if isinstance(baseline, str) else None
            missing = ["verified_surface_water_change", "usable_coverage"]
            if baseline_id is None:
                missing.append("baseline_scene")
            return WaterEvidenceOutcome(
                WaterloggingEvidence(
                    observed_at=datetime.fromisoformat(captured.replace("Z", "+00:00")).astimezone(
                        UTC
                    ),
                    source="copernicus_sentinel_1",
                    scene_id=scene_id,
                    baseline_scene_id=baseline_id,
                    coverage_pct=None,
                    evidence_present=["current_sar_scene"]
                    + (["baseline_sar_scene"] if baseline_id else []),
                    evidence_missing=missing,
                    quality_usable=False,
                    policy_verified=False,
                )
            )
        except httpx.TimeoutException:
            return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_TIMEOUT.value)
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            logger.warning("copernicus water evidence request failed", exc_info=True)
            return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_ERROR.value)


SentinelProvider = CopernicusProvider


def _polygon_seed(polygon: dict) -> int:
    return int(hashlib.sha256(str(polygon.get("coordinates", polygon)).encode()).hexdigest(), 16)


class MockSatelliteProvider:
    name = SatelliteProviderName.MOCK.value

    async def fetch_scene(self, polygon: dict, *, capture_before: date) -> FetchOutcome:
        seed = _polygon_seed(polygon)
        ndvi_target, ndmi_target, nir = 0.35 + (seed % 40) / 100, 0.10 + (seed % 30) / 100, 0.45
        red = round(nir * (1 - ndvi_target) / (1 + ndvi_target), 4)
        swir = round(nir * (1 - ndmi_target) / (1 + ndmi_target), 4)
        bands = BandReflectance(
            red=red, nir=nir, red_edge=round(red + 0.6 * (nir - red), 4), swir=swir, blue=0.06
        )
        return FetchOutcome(
            ProviderScene(
                capture_date=capture_before - timedelta(days=1 + seed % 5),
                provider=self.name,
                cloud_cover=float(seed % 20),
                resolution_m=10.0,
                bands=bands,
                index_stats={"ndvi": (ndvi_target, ndvi_target - 0.05, ndvi_target + 0.05, 0.05)},
                is_sample=True,
                metadata={"note": "sample data (development only)"},
            )
        )

    async def fetch_water_evidence(
        self, polygon: dict, *, capture_before: date
    ) -> WaterEvidenceOutcome:
        return WaterEvidenceOutcome(None, UnavailableReason.NO_IMAGERY.value)

    async def render_scene_images(
        self, polygon: dict, *, capture_date: date, scene_id: str
    ) -> tuple[dict[str, str], str | None]:
        return {}, None


def get_default_provider() -> SatelliteProvider:
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if SATELLITE_PROVIDER == SatelliteProviderName.MOCK.value and environment in {
        "development",
        "test",
    }:
        return MockSatelliteProvider()
    return CopernicusProvider()
