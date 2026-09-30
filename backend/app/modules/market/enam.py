"""eNAM (National Agriculture Market) price provider — second official source.

Reads the public trade-data feed behind the eNAM dashboard
(https://enam.gov.in/web/dashboard/trade-data): one POST per state per day
returns every APMC/commodity traded that day with min/modal/max prices.
No API key. Prices are verified government trade data, same standing as
Agmarknet; nothing is estimated or fabricated.

eNAM's commodity/APMC filters need exact dropdown names, so we always fetch the
whole state for a day and filter locally (substring, like the repository).
Only per-quintal rows are kept, matching the rest of the market module.
"""
from __future__ import annotations

import asyncio
import time
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.timezone import today_ist
from app.modules.market.constants import (
    ENAM_LOOKBACK_DAYS,
    ENAM_MAX_RETRIES,
    ENAM_REFERER,
    ENAM_TIMEOUT_SECONDS,
    ENAM_TRADE_DATA_URL,
    SOURCE_ENAM,
    PriceUnit,
)
from app.modules.market.exceptions import MarketDataUnavailableError
from app.modules.market.provider import PriceQuery, ProviderPrice
from app.modules.market.relay import get_market_http_client

logger = get_logger("market.enam")

_ALL_APMCS = "-- Select APMCs --"
_ALL_COMMODITIES = "-- Select Commodity --"
_QUINTAL_UNITS = {"qui", "qtl", "quintal", "quintals", "qt"}
_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": ENAM_REFERER,
    "Origin": "https://enam.gov.in",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Mobile Safari/537.36"
    ),
}


def _pick(record: dict[str, Any], *keys: str) -> Any:
    lowered = {str(k).lower(): v for k, v in record.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def _price(value: Any) -> float | None:
    try:
        parsed = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _title(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return text.title() if text.isupper() else text


def _parse_date(value: Any, fallback: date) -> date:
    text = str(value or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return fallback


def parse_enam_record(record: dict[str, Any], *, trade_day: date) -> ProviderPrice | None:
    """Normalize one eNAM row; ``None`` if unusable or not priced per quintal."""
    unit = str(_pick(record, "commodity_uom", "uom", "unit") or "qui").strip().lower().rstrip(".")
    if unit not in _QUINTAL_UNITS:
        return None
    modal = _price(_pick(record, "modal_price", "modal"))
    minimum = _price(_pick(record, "min_price", "minimum_price", "min"))
    maximum = _price(_pick(record, "max_price", "maximum_price", "max"))
    if modal is None and minimum is None and maximum is None:
        return None
    modal = modal or maximum or minimum
    minimum = minimum or modal
    maximum = maximum or modal
    commodity = _title(_pick(record, "commodity", "commodity_name"))
    market = _title(_pick(record, "apmc", "apmc_name", "market"))
    if not commodity or not market:
        return None
    return ProviderPrice(
        commodity=commodity,
        variety="",
        market=market,
        district="",  # eNAM reports the APMC, not its district.
        state=_title(_pick(record, "state", "state_name")),
        minimum_price=float(minimum),
        maximum_price=float(maximum),
        modal_price=float(modal),
        unit=PriceUnit.QUINTAL.value,
        price_date=_parse_date(_pick(record, "created_at", "date", "trade_date"), trade_day),
        source=SOURCE_ENAM,
    )


def _contains(value: str, needle: str | None) -> bool:
    return not needle or needle.strip().lower() in value.lower()


class EnamProvider:
    """eNAM daily trade prices for a state, with timeout + bounded retries."""

    source = SOURCE_ENAM

    def __init__(
        self,
        *,
        url: str = ENAM_TRADE_DATA_URL,
        timeout: float = ENAM_TIMEOUT_SECONDS,
        max_retries: int = ENAM_MAX_RETRIES,
        lookback_days: int = ENAM_LOOKBACK_DAYS,
        default_state: str = "Tamil Nadu",
        today: date | None = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.max_retries = max(1, max_retries)
        self.lookback_days = max(1, lookback_days)
        self.default_state = default_state
        self._today = today

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

    async def _latest_state_prices(self, state: str) -> list[ProviderPrice]:
        today = self._today or today_ist()
        reached = False
        for back in range(self.lookback_days):
            day = today - timedelta(days=back)
            try:
                rows = await self._fetch_day(state, day)
            except MarketDataUnavailableError:
                continue  # try an earlier day; a later success still counts
            reached = True
            prices = [p for r in rows if isinstance(r, dict) and (p := parse_enam_record(r, trade_day=day))]
            if prices:
                return prices
        if not reached:
            raise MarketDataUnavailableError()
        return []  # reachable, but no trades reported in the lookback window

    async def _fetch_day(self, state: str, day: date) -> list[Any]:
        form = {
            "language": "en",
            "stateName": state.upper(),
            "apmcName": _ALL_APMCS,
            "commodityName": _ALL_COMMODITIES,
            "fromDate": day.isoformat(),
            "toDate": day.isoformat(),
        }
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            started = time.perf_counter()
            try:
                response = await get_market_http_client().post(
                    self.url, data=form, headers=_HEADERS, timeout=self.timeout
                )
                response.raise_for_status()
                payload = response.json()
                rows = payload.get("data") if isinstance(payload, dict) else payload
                if not isinstance(rows, list):
                    raise ValueError("eNAM payload has no data list")
                logger.info(
                    "provider=enam attempt=%s outcome=success day=%s rows=%s latency_ms=%s",
                    attempt, day, len(rows), round((time.perf_counter() - started) * 1000),
                )
                return rows
            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    "provider=enam attempt=%s outcome=failed category=http_status status=%s",
                    attempt, exc.response.status_code,
                )
                if exc.response.status_code < 500:
                    break
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
                logger.warning(
                    "provider=enam attempt=%s outcome=failed category=transport_error latency_ms=%s",
                    attempt, round((time.perf_counter() - started) * 1000),
                )
            except ValueError as exc:  # non-JSON / unexpected shape
                last_error = exc
                logger.warning("provider=enam attempt=%s outcome=failed category=schema_error", attempt)
            if attempt < self.max_retries:
                await asyncio.sleep(min(0.5 * 2 ** (attempt - 1), 4.0))
        raise MarketDataUnavailableError() from last_error
