"""Soil data providers (docs: provider abstraction; future lab/gov/satellite/OCR).

``SoilProvider`` is the seam that supplies soil data *from outside the app* — a
government soil dataset, an accredited laboratory API, a satellite soil layer, or
Gemini OCR of an uploaded Soil Health Card (docs/AI_DECISION_MATRIX → Soil Report
PDF → Gemini). V1 ships a ``MockSoilProvider`` that returns **nothing**: it never
fabricates a soil value (docs/PRODUCT_RULES.md). Farmer-entered values are the only
source of truth in V1. Future providers implement the same Protocol and are
selected in ``get_default_provider`` with no change to the rest of the module.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from typing import Any, Protocol

import httpx

from app.core.cache import Cache, InMemoryTTLCache, build_cache
from app.core.logging import get_logger
from app.modules.farms.geo import InvalidPolygonError, centroid, extract_ring, validate_ring

logger = get_logger("soil.provider")


@dataclass(frozen=True)
class ProviderSoilData:
    """Soil values from an external dataset (future). Any field may be ``None``."""

    ph: float | None = None
    organic_carbon: float | None = None
    nitrogen: float | None = None
    phosphorus: float | None = None
    potassium: float | None = None
    ec_salinity: float | None = None
    water_holding_capacity: float | None = None
    drainage: str | None = None
    soil_type: str | None = None
    micronutrients: dict[str, float] = field(default_factory=dict)
    source: str | None = None
    confidence: int | None = None


@dataclass(frozen=True)
class ParsedReport:
    """The result of parsing an uploaded report (future Gemini OCR / lab API)."""

    values: ProviderSoilData
    lab_name: str | None = None
    test_date: str | None = None


@dataclass(frozen=True)
class RemoteSoilEstimate:
    indicator: str
    value: float
    unit: str
    provider: str
    model_version: str
    scene_id: str
    aoi_hash: str
    capture_date: date
    resolution_m: float
    coverage_pct: float
    uncertainty_low: float | None
    uncertainty_high: float | None


@dataclass(frozen=True)
class RemoteSoilOutcome:
    estimates: tuple[RemoteSoilEstimate, ...] = ()
    status: str = "insufficient_data"
    reason: str = "provider_not_configured"


class SoilProvider(Protocol):
    """Supplies soil data from an external source. The external seam."""

    name: str

    async def fetch_location_soil(
        self, latitude: float, longitude: float
    ) -> ProviderSoilData | None: ...

    async def parse_report(self, report_url: str, mime_type: str | None) -> ParsedReport | None: ...

    async def fetch_remote_estimates(self, aoi: dict) -> RemoteSoilOutcome: ...


class MockSoilProvider:
    """No external soil source in V1 — returns nothing, fabricates nothing."""

    name = "mock"

    async def fetch_location_soil(
        self, latitude: float, longitude: float
    ) -> ProviderSoilData | None:
        # No verified location soil dataset wired in → no data (never invented).
        logger.info("no location soil dataset configured (%.4f, %.4f)", latitude, longitude)
        return None

    async def parse_report(self, report_url: str, mime_type: str | None) -> ParsedReport | None:
        # No OCR / lab API wired in → the farmer supplies the values (never invented).
        return None

    async def fetch_remote_estimates(self, aoi: dict) -> RemoteSoilOutcome:
        return RemoteSoilOutcome()


class UnavailableSoilProvider:
    """Production-safe null provider; it never returns sample soil values."""

    name = "unavailable"

    async def fetch_location_soil(
        self, latitude: float, longitude: float
    ) -> ProviderSoilData | None:
        return None

    async def parse_report(self, report_url: str, mime_type: str | None) -> ParsedReport | None:
        return None

    async def fetch_remote_estimates(self, aoi: dict) -> RemoteSoilOutcome:
        return RemoteSoilOutcome(
            status="remote_estimation_unavailable",
            reason="provider_not_configured",
        )


# ISRIC SoilGrids v2.0 (docs.isric.org) -- a real, free, no-key-required global
# soil-property map (250 m resolution) built from decades of soil profile
# observations + environmental covariates (Poggio et al. 2021, SOIL 7:217-240,
# https://doi.org/10.5194/soil-7-217-2021). It is a *compiled model*, not a
# fresh measurement -- there is no acquisition/capture date the way a satellite
# scene has one, so we report it honestly as a model estimate (evidence.py:
# EvidenceType.REMOTE_SENSING_ESTIMATE / MODEL_ESTIMATE, precedence 1 -- lowest,
# never overrides a farmer-submitted lab value) with the publication date, not
# today's date. Point-based at the AOI centroid; SoilGrids has no polygon
# aggregation endpoint. Fair use per ISRIC: 5 requests/minute; the API is
# labelled beta, so failures are treated as ordinary and never fatal.
_SOILGRIDS_RELEASE_DATE = date(2021, 6, 14)  # Poggio et al. 2021 publication date
_SOILGRIDS_MODEL_VERSION = "ISRIC SoilGrids v2.0 (Poggio et al. 2021)"
_SOILGRIDS_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


@lru_cache(maxsize=1)
def _shared_soilgrids_cache() -> Cache:
    return build_cache(namespace="soilgrids", ttl_seconds=_SOILGRIDS_CACHE_TTL_SECONDS)


class SoilGridsProvider:
    """Real remote soil-property estimates from ISRIC SoilGrids (see module docs
    above). Only properties that map cleanly onto this app's existing parameter
    set are used: pH (``phh2o``), organic carbon (``soc``, g/kg -> %), and
    particle-size composition (``clay``/``sand``/``silt``, g/kg -> %, added
    2026-08-19 to feed a coarse texture estimate -- see
    ``classify_texture_bucket`` below). Confirmed against ISRIC's own published
    OpenAPI spec for /properties/query (the full valid ``property`` enum is
    bdod, cec, cfvo, clay, nitrogen, ocd, ocs, phh2o, sand, silt, soc, wv0010,
    wv0033, wv1500) -- SoilGrids does not publish phosphorus, potassium, or
    EC/salinity at all, so those are never estimated here: absence stays
    absence, never invented. (A free global soil-salinity layer does exist --
    "Global Soil Salinity Maps 1986-2016" -- but only via Google Earth Engine,
    a separate credentialed service this app doesn't integrate; not wired up.)
    """

    name = "soilgrids"
    BASE_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    DEPTH_LABEL = "0-5cm"  # topsoil, closest to a Soil Health Card sample depth
    # SoilGrids property name -> (our indicator name, extra factor applied
    # *after* the response's own unit_measure.d_factor, unit label).
    # Confirmed against ISRIC's published units/conversion-factor table
    # (docs.isric.org SoilGrids FAQ) -- the two properties here do NOT share
    # the same conventional unit after dividing by d_factor:
    #   - soc: mapped g/kg, d_factor 10 -> conventional unit is g/kg (NOT
    #     percent yet), so we apply one more / 10 (extra_factor 0.1) to get %.
    #   - clay/sand/silt: mapped g/kg, d_factor 10 -> conventional unit is
    #     ALREADY g/100g (i.e. percent). No further conversion -- extra_factor
    #     must stay 1.0, or values silently come out 10x too small (caught by
    #     test_texture_composition_produces_three_percentage_estimates).
    _PROPERTIES: dict[str, tuple[str, float, str]] = {
        "phh2o": ("ph", 1.0, "pH"),
        "soc": ("organic_carbon", 0.1, "%"),
        "clay": ("clay_pct", 1.0, "%"),
        "sand": ("sand_pct", 1.0, "%"),
        "silt": ("silt_pct", 1.0, "%"),
    }

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        cache: Cache | None = None,
    ) -> None:
        self._client = client
        # Tests/custom clients remain isolated. Production instances share the
        # Redis-backed cache selected by CACHE_BACKEND.
        self._cache = cache or (
            InMemoryTTLCache(namespace="soilgrids-test", ttl_seconds=60)
            if client is not None
            else _shared_soilgrids_cache()
        )

    async def fetch_location_soil(
        self, latitude: float, longitude: float
    ) -> ProviderSoilData | None:
        # Kept unimplemented for this point-lookup Protocol method -- the app
        # only calls fetch_remote_estimates (GET /soil/remote) today, and
        # returning None here is the same honest "no data" every other
        # provider gives when a capability isn't wired up.
        return None

    async def parse_report(self, report_url: str, mime_type: str | None) -> ParsedReport | None:
        return None

    async def fetch_remote_estimates(self, aoi: dict) -> RemoteSoilOutcome:
        try:
            ring = validate_ring(extract_ring(aoi))
            center_lat, center_lon = centroid(ring)
        except (InvalidPolygonError, TypeError, ValueError):
            return RemoteSoilOutcome(status="remote_estimation_unavailable", reason="invalid_aoi")

        # SoilGrids is a raster and a valid field can have a masked centroid
        # (water, nodata, or a boundary cell). Try the centroid first, then a
        # maximum of four points halfway toward distinct field vertices. The
        # halfway construction keeps fallback points inside ordinary farm
        # polygons and avoids pretending that one neighbouring cell represents
        # the whole farm. We stop at the first usable cell to respect ISRIC's
        # five-requests-per-minute fair-use guidance.
        candidates = [(center_lat, center_lon)]
        for lon, lat in ring:
            candidate = (
                round((center_lat + lat) / 2, 7),
                round((center_lon + lon) / 2, 7),
            )
            if candidate not in candidates:
                candidates.append(candidate)
            if len(candidates) == 5:
                break

        client = self._client
        owns_client = client is None
        if owns_client:
            # The mobile request budget is 20 seconds. All candidate cells are
            # fetched concurrently with a bounded provider timeout, rather than
            # serially consuming up to 75 seconds.
            client = httpx.AsyncClient(timeout=8.0)
        try:
            results = await asyncio.gather(
                *(self._fetch_payload(client, lat=lat, lon=lon) for lat, lon in candidates),
                return_exceptions=True,
            )
            reasons: list[str] = []
            for (lat, lon), result in zip(candidates, results, strict=True):
                if isinstance(result, BaseException):
                    reasons.append("provider_error")
                    continue
                payload, reason = result
                if reason is not None:
                    reasons.append(reason)
                    continue
                try:
                    estimates = self._parse_response(payload, lat=lat, lon=lon, aoi=aoi)
                except Exception:  # never let a schema surprise fabricate or crash
                    logger.warning("soilgrids response could not be parsed", exc_info=True)
                    reasons.append("provider_error")
                    continue
                if estimates:
                    return RemoteSoilOutcome(
                        estimates=tuple(estimates), status="available", reason="none"
                    )
            if reasons and len(reasons) == len(candidates):
                reason = (
                    "provider_rate_limited"
                    if "provider_rate_limited" in reasons
                    else "provider_timeout"
                    if "provider_timeout" in reasons
                    else "provider_error"
                )
                return RemoteSoilOutcome(
                    status="remote_estimation_unavailable", reason=reason
                )
        finally:
            if owns_client:
                await client.aclose()
        return RemoteSoilOutcome(
            status="remote_estimation_unavailable", reason="no_data_for_location"
        )

    async def _fetch_payload(
        self, client: httpx.AsyncClient, *, lat: float, lon: float
    ) -> tuple[Any | None, str | None]:
        cache_key = f"v1:{lat:.7f}:{lon:.7f}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, dict):
            return cached, None
        params = [("lon", lon), ("lat", lat)]
        params += [("property", name) for name in self._PROPERTIES]
        params += [("depth", self.DEPTH_LABEL)]
        params += [("value", value) for value in ("mean", "Q0.05", "Q0.95")]
        try:
            response = await client.get(self.BASE_URL, params=params)
        except httpx.TimeoutException:
            logger.warning("soilgrids request timed out")
            return None, "provider_timeout"
        except httpx.HTTPError:
            logger.warning("soilgrids request failed", exc_info=True)
            return None, "provider_error"
        if response.status_code == 429:
            return None, "provider_rate_limited"
        if response.status_code != 200:
            logger.warning("soilgrids returned status %s", response.status_code)
            return None, "provider_error"
        try:
            payload = response.json()
        except ValueError:
            return None, "provider_error"
        if not isinstance(payload, dict):
            return None, "provider_error"
        self._cache.set(cache_key, payload)
        return payload, None

    def _parse_response(
        self, payload: Any, *, lat: float, lon: float, aoi: dict
    ) -> list[RemoteSoilEstimate]:
        layers = payload.get("properties", {}).get("layers") if isinstance(payload, dict) else None
        if not isinstance(layers, list):
            return []
        aoi_hash = hashlib.sha256(json.dumps(aoi, sort_keys=True).encode()).hexdigest()[:16]
        estimates: list[RemoteSoilEstimate] = []
        for layer in layers:
            if not isinstance(layer, dict):
                continue
            soilgrids_name = layer.get("name")
            mapping = self._PROPERTIES.get(soilgrids_name)
            if mapping is None:
                continue
            indicator, extra_factor, unit = mapping
            d_factor = (layer.get("unit_measure") or {}).get("d_factor")
            if not isinstance(d_factor, int | float) or d_factor <= 0:
                continue
            depths = layer.get("depths")
            depth_entry = next(
                (
                    d
                    for d in depths or []
                    if isinstance(d, dict) and d.get("label") == self.DEPTH_LABEL
                ),
                None,
            )
            if depth_entry is None:
                continue
            values = depth_entry.get("values") or {}
            mean = values.get("mean")
            if not isinstance(mean, int | float):
                continue  # SoilGrids returns null for masked/no-data cells
            low = values.get("Q0.05")
            high = values.get("Q0.95")

            def convert(
                raw: Any,
                divisor: float = float(d_factor),
                factor: float = extra_factor,
            ) -> float | None:
                if not isinstance(raw, int | float):
                    return None
                return round((raw / divisor) * factor, 3)

            estimates.append(
                RemoteSoilEstimate(
                    indicator=indicator,
                    value=convert(mean),
                    unit=unit,
                    provider=self.name,
                    model_version=_SOILGRIDS_MODEL_VERSION,
                    scene_id=f"soilgrids:{lat:.4f},{lon:.4f}",
                    aoi_hash=aoi_hash,
                    capture_date=_SOILGRIDS_RELEASE_DATE,
                    resolution_m=250.0,
                    coverage_pct=100.0,
                    uncertainty_low=convert(low),
                    uncertainty_high=convert(high),
                )
            )
        return estimates


def get_default_provider() -> SoilProvider:
    """Select an explicit development mock, the real SoilGrids adapter, or fail
    closed. SoilGrids needs no credentials, so it stays opt-in (SOIL_PROVIDER=
    soilgrids) rather than on by default -- it's a beta third-party API and a
    decades-old compiled model, not a fresh measurement; production should turn
    it on deliberately, the same way R2 credentials gate satellite imagery."""
    import os

    configured = os.getenv("SOIL_PROVIDER", "").lower()
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if configured == "mock" and environment in {"development", "test"}:
        logger.info("soil provider: explicit development mock")
        return MockSoilProvider()
    if configured == "soilgrids":
        logger.info("soil provider: ISRIC SoilGrids (real, remote estimates only)")
        return SoilGridsProvider()
    if configured:
        logger.warning("soil provider unavailable: configured adapter is not installed")
    else:
        logger.info("soil provider unavailable: no real adapter configured")
    return UnavailableSoilProvider()
