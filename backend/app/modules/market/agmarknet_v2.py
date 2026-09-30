"""Agmarknet 2.0 price provider — second official source.

The new Agmarknet portal (https://agmarknet.gov.in) serves a public JSON API at
``api.agmarknet.gov.in/v1``. Its state daily report lists every reporting
market (APMCs and Uzhavar Sandhais) with min/max/modal price per commodity and
variety — the same Ministry data as data.gov.in, but from a separate system,
so one being down does not take the other with it. No API key.

Verified 2026-10-01 from India:
* ``GET /location/state?page_size=100``            -> ``states[].id / state_name``
* ``GET /market-district-state``                   -> market -> district list
* ``GET /prices-and-arrivals/commodity-wise/daily-report-state
       ?date=YYYY-MM-DD&stateIds=<id>&includeExcel=false``
                                                   -> ``markets[].commodityGroups[]
                                                        .commodities[].data[]``
Only ₹/quintal rows are kept, matching the rest of the market module.
"""
from __future__ import annotations

import asyncio
import time
from datetime import date, timedelta
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.timezone import today_ist
from app.modules.market.constants import (
    AGMARKNET_V2_BASE_URL,
    AGMARKNET_V2_LOOKBACK_DAYS,
    AGMARKNET_V2_MAX_RETRIES,
    AGMARKNET_V2_TIMEOUT_SECONDS,
    SOURCE_AGMARKNET_V2,
    PriceUnit,
)
from app.modules.market.exceptions import MarketDataUnavailableError
from app.modules.market.provider import PriceQuery, ProviderPrice
from app.modules.market.relay import get_market_http_client

logger = get_logger("market.agmarknet_v2")

# The upstream drops connections that don't look like its own web app.
_HEADERS = {
    "Accept": "application/json",
    "Referer": "https://agmarknet.gov.in/",
    "Origin": "https://agmarknet.gov.in",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
}


def _key(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _price(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _is_quintal(unit: Any) -> bool:
    text = _key(unit)
    return not text or "quintal" in text or text.endswith("qtl")


def parse_state_report(
    payload: dict[str, Any],
    *,
    state: str,
    trade_day: date,
    districts: dict[str, str] | None = None,
) -> list[ProviderPrice]:
    """Flatten one state daily report into normalized ₹/quintal prices."""
    districts = districts or {}
    prices: list[ProviderPrice] = []
    for market in payload.get("markets") or []:
        if not isinstance(market, dict):
            continue
        market_name = _clean(market.get("marketName"))
        if not market_name:
            continue
        district = districts.get(_key(market_name), "")
        for group in market.get("commodityGroups") or []:
            for commodity in (group or {}).get("commodities") or []:
                commodity_name = _clean((commodity or {}).get("commodityName"))
                if not commodity_name:
                    continue
                for row in commodity.get("data") or []:
                    if not isinstance(row, dict) or not _is_quintal(row.get("unitOfPrice")):
                        continue
                    modal = _price(row.get("modalPrice"))
                    minimum = _price(row.get("minimumPrice"))
                    maximum = _price(row.get("maximumPrice"))
                    if modal is None and minimum is None and maximum is None:
                        continue
                    modal = modal or maximum or minimum
                    prices.append(
                        ProviderPrice(
                            commodity=commodity_name,
                            variety=_clean(row.get("variety")),
                            market=market_name,
                            district=district,
                            state=state,
                            minimum_price=float(minimum or modal),
                            maximum_price=float(maximum or modal),
                            modal_price=float(modal),
                            unit=PriceUnit.QUINTAL.value,
                            price_date=trade_day,
                            source=SOURCE_AGMARKNET_V2,
                        )
                    )
    return prices


def _contains(value: str, needle: str | None) -> bool:
    return not needle or needle.strip().casefold() in value.casefold()


class AgmarknetV2Provider:
    """Agmarknet 2.0 state daily report, with timeout + bounded retries."""

    source = SOURCE_AGMARKNET_V2

    def __init__(
        self,
        *,
        base_url: str = AGMARKNET_V2_BASE_URL,
        timeout: float = AGMARKNET_V2_TIMEOUT_SECONDS,
        max_retries: int = AGMARKNET_V2_MAX_RETRIES,
        lookback_days: int = AGMARKNET_V2_LOOKBACK_DAYS,
        default_state: str = "Tamil Nadu",
        today: date | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(1, max_retries)
        self.lookback_days = max(1, lookback_days)
        self.default_state = default_state
        self._today = today
        self._state_ids: dict[str, int] | None = None
        self._state_names: dict[str, str] = {}
        self._districts: dict[int, dict[str, str]] | None = None

    async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]:
        prices = await self._latest_state_prices(query.state or self.default_state)
        matched = [
            p
            for p in prices
            if _contains(p.commodity, query.commodity)
            and _contains(p.market, query.market)
            and _contains(p.district, query.district)
        ]
        return matched[query.offset : query.offset + query.limit]

    async def fetch_all_prices(self, query: PriceQuery, *, max_pages: int = 1) -> list[ProviderPrice]:
        """Whole-state sync (worker): every row for the latest day with data."""
        return await self._latest_state_prices(query.state or self.default_state)

    # ------------------------------------------------------------------ #
    async def _latest_state_prices(self, state: str) -> list[ProviderPrice]:
        state_id, state_name = await self._state(state)
        districts = await self._district_map(state_id)
        today = self._today or today_ist()
        reached = False
        for back in range(self.lookback_days):
            day = today - timedelta(days=back)
            try:
                payload = await self._get(
                    "/prices-and-arrivals/commodity-wise/daily-report-state",
                    {"date": day.isoformat(), "stateIds": state_id, "includeExcel": "false"},
                )
            except MarketDataUnavailableError:
                continue  # an earlier day may still answer
            reached = True
            if not isinstance(payload, dict):
                continue
            prices = parse_state_report(payload, state=state_name, trade_day=day, districts=districts)
            if prices:
                return prices
        if not reached:
            raise MarketDataUnavailableError()
        return []  # reachable, but no market reported in the lookback window

    async def _state(self, state: str) -> tuple[int, str]:
        if self._state_ids is None:
            payload = await self._get("/location/state", {"page_size": 100})
            rows = payload.get("states") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise MarketDataUnavailableError()
            self._state_ids = {
                _key(r.get("state_name")): int(r["id"])
                for r in rows
                if isinstance(r, dict) and r.get("id") is not None
            }
            self._state_names = {
                _key(r.get("state_name")): _clean(r.get("state_name")) for r in rows if isinstance(r, dict)
            }
        state_id = self._state_ids.get(_key(state))
        if state_id is None:
            logger.warning("provider=agmarknet_v2 unknown state=%s", state)
            raise MarketDataUnavailableError()
        return state_id, self._state_names.get(_key(state), _clean(state))

    async def _district_map(self, state_id: int) -> dict[str, str]:
        """Market name -> district for one state. Best effort: prices still
        load (without district) if this lookup fails."""
        if self._districts is None:
            try:
                rows = await self._get("/market-district-state", None)
            except MarketDataUnavailableError:
                return {}
            grouped: dict[int, dict[str, str]] = {}
            for r in rows if isinstance(rows, list) else []:
                if isinstance(r, dict) and r.get("state_id") is not None:
                    grouped.setdefault(int(r["state_id"]), {})[_key(r.get("market_name"))] = _clean(
                        r.get("district_name")
                    )
            self._districts = grouped
        return self._districts.get(state_id, {})

    async def _get(self, path: str, params: dict[str, Any] | None) -> Any:
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            started = time.perf_counter()
            try:
                response = await get_market_http_client().get(
                    url, params=params, headers=_HEADERS, timeout=self.timeout
                )
                response.raise_for_status()
                payload = response.json()
                logger.info(
                    "provider=agmarknet_v2 attempt=%s outcome=success path=%s latency_ms=%s",
                    attempt, path, round((time.perf_counter() - started) * 1000),
                )
                return payload
            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    "provider=agmarknet_v2 attempt=%s outcome=failed category=http_status status=%s path=%s",
                    attempt, exc.response.status_code, path,
                )
                if exc.response.status_code < 500:
                    break
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
                logger.warning(
                    "provider=agmarknet_v2 attempt=%s outcome=failed category=transport_error path=%s latency_ms=%s",
                    attempt, path, round((time.perf_counter() - started) * 1000),
                )
            except ValueError as exc:  # non-JSON body
                last_error = exc
                logger.warning(
                    "provider=agmarknet_v2 attempt=%s outcome=failed category=schema_error path=%s", attempt, path
                )
            if attempt < self.max_retries:
                await asyncio.sleep(min(0.5 * 2 ** (attempt - 1), 4.0))
        raise MarketDataUnavailableError() from last_error
