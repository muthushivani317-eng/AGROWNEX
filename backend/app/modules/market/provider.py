"""Market price providers (docs/BACKEND_ARCHITECTURE.md → provider abstraction).

``MarketPriceProvider`` is the seam that keeps the rest of the module ignorant
of *where* prices come from. V1 ships:

* ``AgmarknetProvider`` — Open Government (data.gov.in / Agmarknet) with timeout
  + bounded retries; used when ``DATA_GOV_API_KEY`` is set.
* ``EnamProvider`` (``enam.py``) — eNAM trade data, the second official source.
* ``FallbackMarketProvider`` — Agmarknet first, eNAM when it is unavailable.
* ``MockMarketProvider`` — deterministic offline data used in dev/tests.

Both official sources reach NIC servers through the India relay when
``MARKET_RELAY_URL`` is configured (see ``relay.py``).

Future providers (state agriculture APIs, local admin prices, paid feeds)
implement the same Protocol and are selected in ``get_default_provider`` with no
change to the service, API or frontend (docs: provider must be replaceable).
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Any, Protocol

import httpx

from app.core.logging import get_logger
from app.core.provider_policy import test_mocks_enabled
from app.modules.market.constants import (
    AGMARKNET_BACKUP_RESOURCE_ID,
    AGMARKNET_FETCH_LIMIT,
    AGMARKNET_MAX_RETRIES,
    AGMARKNET_RESOURCE_ID,
    AGMARKNET_TIMEOUT_SECONDS,
    DATA_GOV_API_KEY,
    DATA_GOV_BASE_URL,
    ENAM_ENABLED,
    SOURCE_AGMARKNET,
    SOURCE_MOCK,
    PriceUnit,
)
from app.modules.market.exceptions import MarketDataUnavailableError

# Relay-aware client under the historical name (tests patch provider.get_http_client).
from app.modules.market.relay import get_market_http_client as get_http_client

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
    offset: int = 0


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


def _record_value(record: dict[str, Any], *keys: str) -> Any:
    """Read a field from either the current or legacy Agmarknet schema.

    data.gov.in has exposed this resource with both normalized lowercase keys
    (``modal_price``) and its older OData-style keys
    (``Modal_x0020_Price``).  Treat both as the same verified source instead of
    silently discarding otherwise valid government records.
    """
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def parse_agmarknet_record(record: dict[str, Any]) -> ProviderPrice | None:
    """Normalize one Agmarknet record; ``None`` if it lacks a usable modal price."""
    modal = _to_float(
        _record_value(record, "modal_price", "Modal_Price", "Modal_x0020_Price")
    )
    minimum = _to_float(
        _record_value(record, "min_price", "Min_Price", "Min_x0020_Price")
    )
    maximum = _to_float(
        _record_value(record, "max_price", "Max_Price", "Max_x0020_Price")
    )
    if modal is None and minimum is None and maximum is None:
        return None
    modal = modal or maximum or minimum
    minimum = minimum or modal
    maximum = maximum or modal
    commodity = str(_record_value(record, "commodity", "Commodity") or "").strip()
    market = str(_record_value(record, "market", "Market") or "").strip()
    if not commodity or not market:
        return None
    return ProviderPrice(
        commodity=commodity,
        variety=str(_record_value(record, "variety", "Variety") or "").strip(),
        grade=(
            str(_record_value(record, "grade", "Grade")).strip() or None
            if _record_value(record, "grade", "Grade")
            else None
        ),
        market=market,
        district=str(_record_value(record, "district", "District") or "").strip(),
        state=str(_record_value(record, "state", "State") or "").strip(),
        minimum_price=float(minimum),
        maximum_price=float(maximum),
        modal_price=float(modal),
        unit=PriceUnit.QUINTAL.value,  # Agmarknet quotes ₹/quintal.
        price_date=_parse_agmarknet_date(
            _record_value(record, "arrival_date", "Arrival_Date")
        ),
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
        backup_resource_id: str = AGMARKNET_BACKUP_RESOURCE_ID,
        timeout: float = AGMARKNET_TIMEOUT_SECONDS,
        max_retries: int = AGMARKNET_MAX_RETRIES,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.resource_id = resource_id
        self.backup_resource_id = backup_resource_id
        self.timeout = timeout
        self.max_retries = max_retries

    def _params(self, query: PriceQuery) -> dict[str, Any]:
        params: dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "limit": max(1, min(query.limit, AGMARKNET_FETCH_LIMIT)),
        }
        if query.offset > 0:
            params["offset"] = query.offset
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
        prices, _ = await self._fetch_with_backup(query)
        return prices

    async def fetch_all_prices(
        self, query: PriceQuery, *, max_pages: int
    ) -> list[ProviderPrice]:
        """Page through every record for ``query`` (e.g. a whole state).

        Used only by the background sync, never on a farmer's request. Stops at
        the first short page; a failure on a later page keeps the pages already
        fetched rather than discarding a partial but valid sync.
        """
        page_size = max(1, min(query.limit, AGMARKNET_FETCH_LIMIT))
        collected: list[ProviderPrice] = []
        for page in range(max(1, max_pages)):
            try:
                prices, raw_count = await self._fetch_with_backup(
                    replace(query, limit=page_size, offset=page * page_size)
                )
            except MarketDataUnavailableError:
                if not collected:
                    raise
                logger.warning("provider=agmarknet sync stopped early at page=%s", page)
                break
            collected.extend(prices)
            if raw_count < page_size:
                break
        return collected

    async def _fetch_with_backup(
        self, query: PriceQuery
    ) -> tuple[list[ProviderPrice], int]:
        try:
            return await self._fetch_from(self.resource_id, query)
        except MarketDataUnavailableError:
            if not self.backup_resource_id:
                raise
            logger.warning("provider=agmarknet primary failed; trying backup resource")
            return await self._fetch_from(self.backup_resource_id, query)

    async def _fetch_from(
        self, resource_id: str, query: PriceQuery
    ) -> tuple[list[ProviderPrice], int]:
        url = f"{self.base_url}/{resource_id}"
        params = self._params(query)
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            started = time.perf_counter()
            try:
                client = get_http_client()
                response = await client.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                try:
                    payload = response.json()
                except ValueError as exc:
                    # A malformed (non-JSON) 200 response — treat like any other
                    # transient upstream failure. Previously this raised an
                    # uncaught JSONDecodeError that propagated past every
                    # MarketDataUnavailableError handler in the codebase,
                    # including the batch refresh job's per-target try/except
                    # (2026-08 pre-release audit) — one bad Agmarknet response
                    # could abort every other farmer's favourited crop/market
                    # still waiting in that same batch.
                    logger.warning(
                        "provider=agmarknet attempt=%s outcome=failed "
                        "category=invalid_payload status=%s latency_ms=%s",
                        attempt,
                        response.status_code,
                        round((time.perf_counter() - started) * 1000),
                    )
                    last_error = exc
                else:
                    records = payload.get("records") if isinstance(payload, dict) else None
                    if not isinstance(records, list):
                        logger.warning(
                            "provider=agmarknet attempt=%s outcome=failed "
                            "category=schema_error status=%s latency_ms=%s",
                            attempt,
                            response.status_code,
                            round((time.perf_counter() - started) * 1000),
                        )
                        last_error = ValueError("Agmarknet records schema is invalid")
                        prices = None
                    else:
                        prices = [
                            price
                            for record in records
                            if isinstance(record, dict)
                            and (price := parse_agmarknet_record(record)) is not None
                        ]
                        if records and not prices:
                            logger.warning(
                                "provider=agmarknet attempt=%s outcome=failed "
                                "category=schema_error status=%s latency_ms=%s",
                                attempt,
                                response.status_code,
                                round((time.perf_counter() - started) * 1000),
                            )
                            last_error = ValueError(
                                "Agmarknet records contained no valid market prices"
                            )
                            prices = None
                    if prices is None:
                        # Retry schema failures just like malformed JSON; a
                        # transient upstream/proxy response must not become a
                        # genuine zero-match result.
                        pass
                    else:
                        logger.info(
                            "provider=agmarknet attempt=%s outcome=success "
                            "category=success status=%s latency_ms=%s records=%s",
                            attempt,
                            response.status_code,
                            round((time.perf_counter() - started) * 1000),
                            len(prices),
                        )
                        return prices, len(records)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
                logger.warning(
                    "provider=agmarknet attempt=%s outcome=failed "
                    "category=transport_error status=none latency_ms=%s",
                    attempt,
                    round((time.perf_counter() - started) * 1000),
                )
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "provider=agmarknet attempt=%s outcome=failed "
                    "category=http_status status=%s latency_ms=%s",
                    attempt,
                    exc.response.status_code,
                    round((time.perf_counter() - started) * 1000),
                )
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


class UnavailableMarketProvider:
    """Never substitutes synthetic prices for an unavailable live source."""

    source = "unavailable"

    async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]:
        raise MarketDataUnavailableError()


class FallbackMarketProvider:
    """Try each official source in order; the first that answers wins.

    Only an *unavailable* source moves on to the next one — a source that
    answers with zero matching rows is a real answer and is returned as is.
    """

    def __init__(self, *providers: MarketPriceProvider) -> None:
        if not providers:
            raise ValueError("FallbackMarketProvider needs at least one provider")
        self.providers = providers
        self.source = providers[0].source

    async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]:
        for index, provider in enumerate(self.providers):
            try:
                return await provider.fetch_prices(query)
            except MarketDataUnavailableError:
                if index == len(self.providers) - 1:
                    raise
                logger.warning("market provider %s unavailable; trying %s",
                               provider.source, self.providers[index + 1].source)
        raise MarketDataUnavailableError()  # pragma: no cover - loop always returns/raises

    async def fetch_all_prices(self, query: PriceQuery, *, max_pages: int) -> list[ProviderPrice]:
        for index, provider in enumerate(self.providers):
            fetch_all = getattr(provider, "fetch_all_prices", None)
            try:
                if fetch_all is not None:
                    return await fetch_all(query, max_pages=max_pages)
                return await provider.fetch_prices(query)
            except MarketDataUnavailableError:
                if index == len(self.providers) - 1:
                    raise
        raise MarketDataUnavailableError()  # pragma: no cover


def official_providers(
    agmarknet: MarketPriceProvider | None = None,
    enam: MarketPriceProvider | None = None,
) -> list[MarketPriceProvider]:
    """Configured official sources in priority order (Agmarknet, then eNAM)."""
    from app.modules.market.enam import EnamProvider  # circular: enam imports this module

    providers: list[MarketPriceProvider] = []
    if DATA_GOV_API_KEY:
        providers.append(agmarknet or AgmarknetProvider())
    if ENAM_ENABLED:
        providers.append(enam or EnamProvider())
    return providers


def get_default_provider() -> MarketPriceProvider:
    """Select the configured provider: official sources first, mock only in tests."""
    if test_mocks_enabled() and not DATA_GOV_API_KEY:
        logger.info("market provider: explicit development/test mock")
        return MockMarketProvider()
    providers = official_providers()
    if not providers:
        logger.warning("market provider unavailable: no official source configured")
        return UnavailableMarketProvider()
    logger.info("market provider: %s", " -> ".join(p.source for p in providers))
    return providers[0] if len(providers) == 1 else FallbackMarketProvider(*providers)
