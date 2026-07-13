"""Market price providers (docs/BACKEND_ARCHITECTURE.md → provider abstraction).

``MarketPriceProvider`` is the seam that keeps the rest of the module ignorant
of *where* prices come from. V1 ships:

* ``AgmarknetProvider`` — Open Government (data.gov.in / Agmarknet) with timeout
  + bounded retries; used when ``DATA_GOV_API_KEY`` is set.
* ``MockMarketProvider`` — deterministic offline data used in dev/tests.

Future providers (eNAM, state agriculture APIs, local admin prices, paid feeds)
implement the same Protocol and are selected in ``get_default_provider`` with no
change to the service, API or frontend (docs: provider must be replaceable).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol

import httpx

from app.core.logging import get_logger
from app.modules.market.constants import (
    AGMARKNET_FETCH_LIMIT,
    AGMARKNET_MAX_RETRIES,
    AGMARKNET_RESOURCE_ID,
    AGMARKNET_TIMEOUT_SECONDS,
    DATA_GOV_API_KEY,
    DATA_GOV_BASE_URL,
    SOURCE_AGMARKNET,
    SOURCE_MOCK,
    PriceUnit,
)
from app.modules.market.exceptions import MarketDataUnavailableError

logger = get_logger("market.provider")


@dataclass(frozen=True)
class ProviderPrice:
    """A normalized price record, independent of the upstream source shape."""

    commodity: str
    variety: str
    market: str
    district: str
    state: str
    minimum_price: float
    maximum_price: float
    modal_price: float
    unit: str
    price_date: date
    source: str
    grade: str | None = None


@dataclass(frozen=True)
class PriceQuery:
    """Filters passed to a provider (docs: filter by crop/district/state/market)."""

    commodity: str | None = None
    market: str | None = None
    district: str | None = None
    state: str | None = None
    limit: int = AGMARKNET_FETCH_LIMIT


class MarketPriceProvider(Protocol):
    """Fetches normalized price records for a query. The single external seam."""

    source: str

    async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]: ...


# --------------------------------------------------------------------------- #
# Open Government / Agmarknet
# --------------------------------------------------------------------------- #
def _to_float(value: Any) -> float | None:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _parse_agmarknet_date(value: Any) -> date:
    text = str(value or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return datetime.now(UTC).date()


def parse_agmarknet_record(record: dict[str, Any]) -> ProviderPrice | None:
    """Normalize one Agmarknet record; ``None`` if it lacks a usable modal price."""
    modal = _to_float(record.get("modal_price"))
    minimum = _to_float(record.get("min_price"))
    maximum = _to_float(record.get("max_price"))
    if modal is None and minimum is None and maximum is None:
        return None
    modal = modal or maximum or minimum
    minimum = minimum or modal
    maximum = maximum or modal
    commodity = str(record.get("commodity") or "").strip()
    market = str(record.get("market") or "").strip()
    if not commodity or not market:
        return None
    return ProviderPrice(
        commodity=commodity,
        variety=str(record.get("variety") or "").strip(),
        grade=(str(record.get("grade")).strip() or None) if record.get("grade") else None,
        market=market,
        district=str(record.get("district") or "").strip(),
        state=str(record.get("state") or "").strip(),
        minimum_price=float(minimum),
        maximum_price=float(maximum),
        modal_price=float(modal),
        unit=PriceUnit.QUINTAL.value,  # Agmarknet quotes ₹/quintal.
        price_date=_parse_agmarknet_date(record.get("arrival_date")),
        source=SOURCE_AGMARKNET,
    )


class AgmarknetProvider:
    """data.gov.in daily mandi price client with timeout + bounded retries."""

    source = SOURCE_AGMARKNET

    def __init__(
        self,
        *,
        api_key: str = DATA_GOV_API_KEY,
        base_url: str = DATA_GOV_BASE_URL,
        resource_id: str = AGMARKNET_RESOURCE_ID,
        timeout: float = AGMARKNET_TIMEOUT_SECONDS,
        max_retries: int = AGMARKNET_MAX_RETRIES,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.resource_id = resource_id
        self.timeout = timeout
        self.max_retries = max_retries

    def _params(self, query: PriceQuery) -> dict[str, Any]:
        params: dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "limit": max(1, min(query.limit, AGMARKNET_FETCH_LIMIT)),
        }
        # data.gov.in filter syntax: filters[field]=value.
        if query.commodity:
            params["filters[commodity]"] = query.commodity
        if query.market:
            params["filters[market]"] = query.market
        if query.district:
            params["filters[district]"] = query.district
        if query.state:
            params["filters[state]"] = query.state
        return params

    async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]:
        url = f"{self.base_url}/{self.resource_id}"
        params = self._params(query)
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    payload = response.json()
                records = payload.get("records", []) if isinstance(payload, dict) else []
                return [
                    price
                    for record in records
                    if (price := parse_agmarknet_record(record)) is not None
                ]
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    # Client error (bad key/params) — no point retrying.
                    raise MarketDataUnavailableError() from exc
                last_error = exc

            if attempt < self.max_retries:
                await asyncio.sleep(min(0.5 * 2 ** (attempt - 1), 4.0))

        logger.warning("Agmarknet fetch failed after %s attempts", self.max_retries)
        raise MarketDataUnavailableError() from last_error


# --------------------------------------------------------------------------- #
# Deterministic mock (offline / dev / tests)
# --------------------------------------------------------------------------- #
@dataclass
class _MockRow:
    commodity: str
    variety: str
    market: str
    district: str
    state: str
    minimum: float
    maximum: float
    modal: float


_MOCK_ROWS: list[_MockRow] = [
    _MockRow("Paddy", "Common", "Thanjavur", "Thanjavur", "Tamil Nadu", 1980, 2120, 2050),
    _MockRow("Rice", "Fine", "Chennai", "Chennai", "Tamil Nadu", 3500, 3900, 3700),
    _MockRow("Tomato", "Local", "Coimbatore", "Coimbatore", "Tamil Nadu", 1200, 1800, 1500),
    _MockRow("Onion", "Big", "Madurai", "Madurai", "Tamil Nadu", 1500, 2200, 1850),
    _MockRow("Groundnut", "Bold", "Salem", "Salem", "Tamil Nadu", 5800, 6400, 6100),
    _MockRow("Sugarcane", "Local", "Erode", "Erode", "Tamil Nadu", 300, 360, 330),
    _MockRow("Cotton", "Medium", "Coimbatore", "Coimbatore", "Tamil Nadu", 6800, 7400, 7100),
    _MockRow("Banana", "Nendran", "Trichy", "Tiruchirappalli", "Tamil Nadu", 2400, 3000, 2700),
]


class MockMarketProvider:
    """Deterministic prices so the module works offline / in dev without a key."""

    source = SOURCE_MOCK

    def __init__(self, *, rows: list[_MockRow] | None = None, today: date | None = None) -> None:
        self._rows = rows if rows is not None else _MOCK_ROWS
        self._today = today

    @staticmethod
    def _matches(value: str, needle: str | None) -> bool:
        return needle is None or needle.strip().lower() in value.lower()

    async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]:
        today = self._today or datetime.now(UTC).date()
        results: list[ProviderPrice] = []
        for row in self._rows:
            if not (
                self._matches(row.commodity, query.commodity)
                and self._matches(row.market, query.market)
                and self._matches(row.district, query.district)
                and self._matches(row.state, query.state)
            ):
                continue
            results.append(
                ProviderPrice(
                    commodity=row.commodity,
                    variety=row.variety,
                    market=row.market,
                    district=row.district,
                    state=row.state,
                    minimum_price=row.minimum,
                    maximum_price=row.maximum,
                    modal_price=row.modal,
                    unit=PriceUnit.QUINTAL.value,
                    price_date=today,
                    source=SOURCE_MOCK,
                )
            )
        return results[: query.limit]


def get_default_provider() -> MarketPriceProvider:
    """Select the configured provider (docs: Agmarknet first, mock fallback)."""
    if DATA_GOV_API_KEY:
        logger.info("market provider: Agmarknet (data.gov.in)")
        return AgmarknetProvider()
    logger.info("market provider: mock (no DATA_GOV_API_KEY)")
    return MockMarketProvider()
