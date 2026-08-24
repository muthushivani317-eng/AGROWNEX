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
from app.modules.satellite.engine import BandReflectance, IndexValues, compute_indices
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


def _index_colour_evalscript(expression: str, low: float, high: float) -> str:
    """Render a transparent, continuous index heatmap (red → amber → green)."""
    return f"""//VERSION=3
function setup() {{
  return {{ input:[{{bands:[\"B03\",\"B04\",\"B05\",\"B08\",\"B11\",\"dataMask\"]}}],
    output:{{bands:4}} }};
}}
function evaluatePixel(s) {{
  if (!s.dataMask) return [0,0,0,0];
  var v={expression}; var n=Math.max(0,Math.min(1,(v-({low}))/(({high})-({low}))));
  return n < .5 ? [1, 2*n, .08, s.dataMask] : [2*(1-n), .82, .12, s.dataMask];
}}"""


_NDRE_COLOR_EVALSCRIPT = _index_colour_evalscript("(s.B08-s.B05)/(s.B08+s.B05+0.000001)", -0.1, 0.7)
_NDMI_COLOR_EVALSCRIPT = _index_colour_evalscript("(s.B08-s.B11)/(s.B08+s.B11+0.000001)", -0.5, 0.6)
_CROP_STRESS_EVALSCRIPT = _index_colour_evalscript(
    "0.65*((s.B08-s.B04)/(s.B08+s.B04+0.000001))+0.35*((s.B08-s.B11)/(s.B08+s.B11+0.000001))",
    -0.35,
    0.75,
)
_BARE_COVER_EVALSCRIPT = """//VERSION=3
function setup(){return {input:[{bands:["B04","B08","dataMask"]}],output:{bands:4}};}
function evaluatePixel(s){
  if(!s.dataMask)return[0,0,0,0];
  var n=(s.B08-s.B04)/(s.B08+s.B04+.000001);
  return n<.18?[.65,.43,.22,1]:[.12,.62,.18,1];
}
"""
_SURFACE_WATER_EVALSCRIPT = """//VERSION=3
function setup(){return {input:[{bands:["B03","B11","dataMask"]}],output:{bands:4}};}
function evaluatePixel(s){
  if(!s.dataMask)return[0,0,0,0];
  var w=(s.B03-s.B11)/(s.B03+s.B11+.000001);
  return w>.12?[.05,.42,.9,1]:[.82,.78,.55,1];
}
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
                        f"{start.isoformat()}T00:00:00Z/{capture_before.isoformat()}T23:59:59Z"
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
            field_indices = compute_indices(bands)
            spatial_zones = await self._fetch_spatial_zones(
                token, polygon, capture_date, field_indices
            )
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
                        "spatial_variability_zones": spatial_zones,
                    },
                )
            )
        except httpx.TimeoutException:
            return FetchOutcome(None, UnavailableReason.PROVIDER_TIMEOUT.value)
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            logger.warning("copernicus request failed", exc_info=True)
            return FetchOutcome(None, UnavailableReason.PROVIDER_ERROR.value)

    async def _fetch_spatial_zones(
        self,
        token: str,
        polygon: dict,
        capture_date: date,
        field_indices: IndexValues,
    ) -> list[dict[str, Any]]:
        """Measure several real interior sub-AOIs for variability guidance.

        A failed sub-zone is simply omitted; it never downgrades the already
        valid field-wide numeric scan. Only zones materially different from the
        field mean are returned, so sampling points are not manufactured for a
        homogeneous field.
        """
        try:
            coordinates = polygon["coordinates"][0]
            core = coordinates[:-1] if coordinates[0] == coordinates[-1] else coordinates
            center_lon = sum(point[0] for point in core) / len(core)
            center_lat = sum(point[1] for point in core) / len(core)
            span_lon = max(point[0] for point in core) - min(point[0] for point in core)
            span_lat = max(point[1] for point in core) - min(point[1] for point in core)
        except (KeyError, IndexError, TypeError, ZeroDivisionError):
            return []
        zones: list[dict[str, Any]] = []
        for index, vertex in enumerate(core[:4], start=1):
            lon = (center_lon + float(vertex[0])) / 2
            lat = (center_lat + float(vertex[1])) / 2
            half_lon = max(span_lon / 40, 0.00005)
            half_lat = max(span_lat / 40, 0.00005)
            geometry = {
                "type": "Polygon",
                "coordinates": [
                    [
                        [lon - half_lon, lat - half_lat],
                        [lon + half_lon, lat - half_lat],
                        [lon + half_lon, lat + half_lat],
                        [lon - half_lon, lat + half_lat],
                        [lon - half_lon, lat - half_lat],
                    ]
                ],
            }
            try:
                response = await self._post(
                    self.STATISTICS_URL,
                    headers={"Authorization": f"Bearer {token}"},
                    json=self._statistics_request(geometry, capture_date),
                    timeout=self.timeout,
                )
                if response.status_code != 200:
                    continue
                zone_bands = self._parse_band_means(response.json())
                if zone_bands is None:
                    continue
                zone_indices = compute_indices(zone_bands)
            except StopAsyncIteration:
                break  # exhausted test/client stream; field-wide scan remains valid
            except (httpx.HTTPError, ValueError, TypeError, KeyError):
                continue
            ndvi_delta = self._difference(zone_indices.ndvi, field_indices.ndvi)
            ndmi_delta = self._difference(zone_indices.ndmi, field_indices.ndmi)
            if max(abs(ndvi_delta), abs(ndmi_delta)) < 0.03:
                continue
            poor = ndvi_delta <= -0.03 or ndmi_delta <= -0.03
            zones.append(
                {
                    "zone_id": f"sat-zone-{index}",
                    "geometry": geometry,
                    "variability_class": "lower_vigor_or_moisture"
                    if poor
                    else "higher_vigor_or_moisture",
                    "observation_class": "poor_performing" if poor else "variable",
                    "quality": "usable",
                    "is_sample": False,
                    "ndvi": zone_indices.ndvi,
                    "ndmi": zone_indices.ndmi,
                    "ndre": zone_indices.ndre,
                    "center": {"latitude": round(lat, 7), "longitude": round(lon, 7)},
                    "relative_position": {
                        "x": round(
                            (lon - (center_lon - span_lon / 2)) / max(span_lon, 0.000001), 3
                        ),
                        "y": round(
                            1 - (lat - (center_lat - span_lat / 2)) / max(span_lat, 0.000001), 3
                        ),
                    },
                    "priority": "inspect_first"
                    if poor and ndvi_delta <= ndmi_delta
                    else ("irrigate_first" if poor else "healthy_no_immediate_action"),
                    "suggested_action": "Inspect this zone in the field"
                    if poor
                    else "Recheck after the next scan",
                    "confidence": 0.78,
                    "ndvi_delta": round(ndvi_delta, 3),
                    "ndmi_delta": round(ndmi_delta, 3),
                }
            )
        return zones

    @staticmethod
    def _difference(value: float | None, baseline: float | None) -> float:
        if value is None or baseline is None:
            return 0.0
        return value - baseline

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
            'output:[{id:"bands",bands:5,sampleType:"FLOAT32"},'
            '{id:"dataMask",bands:1}]};}\n'
            "function evaluatePixel(s){let v=s.dataMask&&"
            "![1,3,7,8,9,10].includes(s.SCL);return {bands:"
            "[s.B02,s.B04,s.B05,s.B08,s.B11],dataMask:[v?1:0]};}"
        )
        # Statistical API defaults to SKIP for an incomplete final aggregation
        # interval. Ending at 23:59:59 made this one second shorter than P1D,
        # so a valid HTTP 200 response contained an empty `data` list.
        next_day = capture_date + timedelta(days=1)
        period = {
            "from": f"{capture_date.isoformat()}T00:00:00Z",
            "to": f"{next_day.isoformat()}T00:00:00Z",
        }
        return {
            "input": {
                "bounds": {
                    "geometry": polygon,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [{"type": "sentinel-2-l2a", "dataFilter": {"timeRange": period}}],
            },
            "aggregation": {
                "timeRange": period,
                "aggregationInterval": {"of": "P1D"},
                # Resolution is expressed in the AOI CRS units. The polygon is
                # WGS84 degrees, so 10 here meant a 10-degree pixel and yielded
                # an empty statistical result. 0.0001 degrees is about 11 m.
                "resx": 0.0001,
                "resy": 0.0001,
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
        """Render all farmer-facing layers and upload them to object storage. Never
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
            layers = {
                "ndvi": _NDVI_COLOR_EVALSCRIPT,
                "ndre": _NDRE_COLOR_EVALSCRIPT,
                "ndmi": _NDMI_COLOR_EVALSCRIPT,
                "crop_stress": _CROP_STRESS_EVALSCRIPT,
                "bare_cover": _BARE_COVER_EVALSCRIPT,
                "surface_water": _SURFACE_WATER_EVALSCRIPT,
            }
            for band, evalscript in layers.items():
                rendered = await self._fetch_rendered_image(
                    token, polygon, capture_date, evalscript
                )
                if not rendered:
                    continue
                url = await self.storage.put(
                    key=f"{SATELLITE_IMAGE_PREFIX}/{scene_id}/{band}.png",
                    data=rendered,
                    content_type="image/png",
                )
                images[band] = url
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
                if isinstance(bands, dict):
                    # Sentinel Hub's Statistical API names unnamed output bands
                    # B0, B1, ... . Keep the legacy numeric-key fallback for
                    # previously recorded fixtures/provider-compatible payloads.
                    entry = bands.get(f"B{index}", bands.get(str(index)))
                    if entry is None:
                        return None
                else:
                    entry = bands[index]
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
        """Compare real Sentinel-1 low-backscatter coverage across two acquisitions.

        This is a cautious screening signal, not a flood-depth measurement or field
        safety decision. The assessment layer therefore still requires review.
        """
        if not self.client_id or not self.client_secret:
            return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_NOT_CONFIGURED.value)
        try:
            token, reason = await self._access_token()
            if token is None:
                return WaterEvidenceOutcome(None, reason)
            start = capture_before - timedelta(days=ACQUISITION_LOOKBACK_DAYS * 2)
            response = await self._post(
                self.STAC_URL,
                json={
                    "collections": ["sentinel-1-grd"],
                    "intersects": polygon,
                    "datetime": (
                        f"{start.isoformat()}T00:00:00Z/{capture_before.isoformat()}T23:59:59Z"
                    ),
                    "sortby": [{"field": "properties.datetime", "direction": "desc"}],
                    "limit": 20,
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
            current, baseline = self._compatible_water_scenes(features)
            if current is None:
                return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_ERROR.value)
            scene_id = current.get("id")
            captured = current.get("properties", {}).get("datetime")
            if not isinstance(scene_id, str) or not isinstance(captured, str):
                return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_ERROR.value)
            baseline_id = baseline.get("id") if baseline else None
            baseline_id = baseline_id if isinstance(baseline_id, str) else None
            missing: list[str] = []
            if baseline_id is None:
                missing.append("baseline_scene")
                return WaterEvidenceOutcome(
                    WaterloggingEvidence(
                        observed_at=datetime.fromisoformat(
                            captured.replace("Z", "+00:00")
                        ).astimezone(UTC),
                        source="copernicus_sentinel_1",
                        scene_id=scene_id,
                        baseline_scene_id=None,
                        coverage_pct=None,
                        evidence_present=["current_sar_scene"],
                        evidence_missing=missing,
                    )
                )
            baseline_captured = baseline.get("properties", {}).get("datetime")
            if not isinstance(baseline_captured, str):
                return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_ERROR.value)
            current_stats = await self._water_statistics(token, polygon, captured)
            baseline_stats = await self._water_statistics(token, polygon, baseline_captured)
            if current_stats is None or baseline_stats is None:
                return WaterEvidenceOutcome(None, UnavailableReason.PROCESSING_ERROR.value)
            current_fraction, current_coverage = current_stats
            baseline_fraction, baseline_coverage = baseline_stats
            usable_coverage = min(current_coverage, baseline_coverage)
            quality_usable = usable_coverage >= 60.0
            if not quality_usable:
                missing.append("usable_coverage")
            # Five percentage points avoids interpreting ordinary SAR speckle as
            # a field-scale water change. It remains an unverified screening rule.
            change = "increase" if current_fraction - baseline_fraction >= 0.05 else "none"
            return WaterEvidenceOutcome(
                WaterloggingEvidence(
                    observed_at=datetime.fromisoformat(captured.replace("Z", "+00:00")).astimezone(
                        UTC
                    ),
                    source="copernicus_sentinel_1",
                    scene_id=scene_id,
                    baseline_scene_id=baseline_id,
                    coverage_pct=round(usable_coverage, 1),
                    evidence_present=[
                        "current_sar_scene",
                        "baseline_sar_scene",
                        "surface_water_change",
                        "compatible_baseline",
                    ],
                    evidence_missing=missing,
                    surface_water_change=change,
                    quality_usable=quality_usable,
                    policy_verified=False,
                )
            )
        except httpx.TimeoutException:
            return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_TIMEOUT.value)
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            logger.warning("copernicus water evidence request failed", exc_info=True)
            return WaterEvidenceOutcome(None, UnavailableReason.PROVIDER_ERROR.value)

    @staticmethod
    def _compatible_water_scenes(features: list[Any]) -> tuple[dict | None, dict | None]:
        valid = [
            item
            for item in features
            if isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and isinstance(item.get("properties", {}).get("datetime"), str)
        ]
        if not valid:
            return None, None
        current = valid[0]
        properties = current["properties"]
        compatibility_keys = (
            "sat:relative_orbit",
            "sat:orbit_state",
            "sar:instrument_mode",
            "sar:polarizations",
        )
        baseline = next(
            (
                item
                for item in valid[1:]
                if all(
                    properties.get(key) is None
                    or item["properties"].get(key) == properties.get(key)
                    for key in compatibility_keys
                )
            ),
            None,
        )
        return current, baseline

    @staticmethod
    def _water_statistics_request(polygon: dict, captured: str) -> dict[str, Any]:
        captured_date = datetime.fromisoformat(captured.replace("Z", "+00:00")).date()
        next_day = captured_date + timedelta(days=1)
        period = {
            "from": f"{captured_date.isoformat()}T00:00:00Z",
            "to": f"{next_day.isoformat()}T00:00:00Z",
        }
        evalscript = """
//VERSION=3
function setup(){
  return {
    input:[{bands:["VV","VH","dataMask"]}],
    output:[
      {id:"water",bands:1,sampleType:"FLOAT32"},
      {id:"dataMask",bands:1}
    ]
  };
}
function evaluatePixel(s){
  let vv=10*Math.log(s.VV+0.000001)/Math.LN10;
  let vh=10*Math.log(s.VH+0.000001)/Math.LN10;
  let water=vv<-15&&vh<-20?1:0;
  return {water:[water],dataMask:[s.dataMask]};
}
"""
        return {
            "input": {
                "bounds": {
                    "geometry": polygon,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": "sentinel-1-grd",
                        "dataFilter": {
                            "timeRange": period,
                            "acquisitionMode": "IW",
                            "polarization": "DV",
                            "resolution": "HIGH",
                        },
                        "processing": {
                            "orthorectify": True,
                            "demInstance": "COPERNICUS_30",
                            "backCoeff": "GAMMA0_TERRAIN",
                            "speckleFilter": {
                                "type": "LEE",
                                "windowSizeX": 5,
                                "windowSizeY": 5,
                            },
                        },
                    }
                ],
            },
            "aggregation": {
                "timeRange": period,
                "aggregationInterval": {"of": "P1D"},
                "resx": 0.0001,
                "resy": 0.0001,
                "evalscript": evalscript,
            },
        }

    async def _water_statistics(
        self, token: str, polygon: dict, captured: str
    ) -> tuple[float, float] | None:
        response = await self._post(
            self.STATISTICS_URL,
            headers={"Authorization": f"Bearer {token}"},
            json=self._water_statistics_request(polygon, captured),
            timeout=self.timeout,
        )
        if self._failure(response):
            return None
        try:
            stats = response.json()["data"][0]["outputs"]["water"]["bands"]["B0"]["stats"]
            mean = stats["mean"]
            samples = stats["sampleCount"]
            no_data = stats["noDataCount"]
            if any(
                isinstance(value, bool) or not isinstance(value, int | float)
                for value in (mean, samples, no_data)
            ):
                return None
            total = float(samples)
            valid = total - float(no_data)
            if total <= 0 or valid < 0:
                return None
            return float(mean), 100.0 * valid / total
        except (KeyError, IndexError, TypeError, ZeroDivisionError):
            return None


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
