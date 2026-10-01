"""Backup price ingest + sync status (plan 2 / plan 3 of market reliability).

Plan 1 is the worker syncing data.gov.in + Agmarknet 2.0 (through the India
relay when configured). If that fails, a small uploader on a computer in India
(``scripts/market_backup_uploader.py``) downloads the official Agmarknet 2.0
state report and POSTs it here. The backend parses it with the same parser the
worker uses, so only verified government rows are ever stored — never typed,
estimated or scraped prices.

``sync_status`` is the freshness signal the uploader and the nightly check read.
"""
from __future__ import annotations

import hmac
from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError, ValidationError
from app.core.logging import get_logger
from app.core.timezone import today_ist
from app.modules.market.agmarknet_v2 import parse_state_report
from app.modules.market.constants import MARKET_INGEST_TOKEN
from app.modules.market.models import MarketLocation, MarketPrice
from app.modules.market.repository import MarketRepository

logger = get_logger("market.backup")

MAX_INGEST_AGE_DAYS = 7
STALE_AFTER_DAYS = 2  # markets skip Sundays/holidays; 2 days old is still normal


class BackupIngestIn(BaseModel):
    """One official Agmarknet 2.0 state daily report, as downloaded."""

    state: str = Field(min_length=2, max_length=60)
    trade_day: date
    report: dict[str, Any]
    districts: dict[str, str] = Field(default_factory=dict, max_length=5000)


class BackupIngestOut(BaseModel):
    state: str
    trade_day: date
    saved: int


class SourceCount(BaseModel):
    source: str
    prices: int


class SyncStatusOut(BaseModel):
    state: str
    latest_price_date: date | None
    days_old: int | None
    stale: bool
    prices_on_latest_date: int
    sources_on_latest_date: list[SourceCount]


MIN_INGEST_TOKEN_LENGTH = 32


def verify_ingest_token(token: str | None) -> None:
    """Fail closed: no configured token means the ingest route is disabled."""
    # A short shared secret is guessable, so treat it as "not configured".
    if (
        len(MARKET_INGEST_TOKEN) < MIN_INGEST_TOKEN_LENGTH
        or not token
        or not hmac.compare_digest(token.encode(), MARKET_INGEST_TOKEN.encode())
    ):
        raise UnauthorizedError("Invalid ingest token.")


async def ingest_state_report(session: AsyncSession, payload: BackupIngestIn) -> BackupIngestOut:
    today = today_ist()
    if payload.trade_day > today or payload.trade_day < today - timedelta(days=MAX_INGEST_AGE_DAYS):
        raise ValidationError("trade_day must be within the last 7 days.")
    districts = {" ".join(k.split()).casefold(): " ".join(v.split()) for k, v in payload.districts.items()}
    prices = parse_state_report(
        payload.report, state=" ".join(payload.state.split()), trade_day=payload.trade_day, districts=districts
    )
    if not prices:
        raise ValidationError("The report contained no usable per-quintal prices.")
    await MarketRepository(session).save_prices(prices)
    logger.info("market backup ingest: %s %s -> %s prices", payload.state, payload.trade_day, len(prices))
    return BackupIngestOut(state=payload.state, trade_day=payload.trade_day, saved=len(prices))


async def sync_status(session: AsyncSession, *, state: str) -> SyncStatusOut:
    in_state = func.lower(MarketLocation.state).like(f"%{state.strip().lower()}%")
    base = select(MarketPrice).join(MarketLocation, MarketPrice.market_id == MarketLocation.id).where(in_state)
    latest = (
        await session.execute(base.with_only_columns(func.max(MarketPrice.price_date)))
    ).scalar_one_or_none()
    sources: list[SourceCount] = []
    if latest is not None:
        rows = await session.execute(
            base.where(MarketPrice.price_date == latest)
            .with_only_columns(MarketPrice.source, func.count())
            .group_by(MarketPrice.source)
            .order_by(MarketPrice.source)
        )
        sources = [SourceCount(source=src, prices=n) for src, n in rows.all()]
    days_old = (today_ist() - latest).days if latest else None
    return SyncStatusOut(
        state=state,
        latest_price_date=latest,
        days_old=days_old,
        stale=days_old is None or days_old > STALE_AFTER_DAYS,
        prices_on_latest_date=sum(s.prices for s in sources),
        sources_on_latest_date=sources,
    )
