"""Admin Engine (pure — docs: dashboard/analytics/procurement aggregation).

No I/O. Turns the read-only metrics into the dashboard's overview cards and the
procurement analytics (village-wise / crop-wise / season-wise / quantity trends).
Reuses the produce quantity normalizer and the memory season helper — no duplication
(docs/PRODUCT_RULES.md → No duplicate code). Nothing here fabricates data.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from app.modules.admin.constants import OVERVIEW_METRICS


@dataclass(frozen=True)
class OverviewCard:
    key: str
    value: int | None


def build_overview(counts: dict[str, int | None]) -> list[OverviewCard]:
    """The dashboard overview cards, in the documented order (pure)."""
    return [OverviewCard(key=key, value=counts.get(key)) for key in OVERVIEW_METRICS]


@dataclass(frozen=True)
class ProcurementFact:
    village: str | None
    crop: str | None
    harvest_date: date | datetime | None
    quantity: float
    unit: str


def _as_date(value: date | datetime | None) -> date | None:
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def _kg(quantity: float, unit: str) -> float:
    from app.modules.produce.engine import to_kilograms

    kg = to_kilograms(quantity, unit)
    return kg if kg is not None else 0.0


def _season(d: date) -> str:
    from app.modules.memory.constants import season_for_month

    return season_for_month(d.month)


def _bucket(facts: list[ProcurementFact], key_fn) -> list[dict]:  # noqa: ANN001
    counts: dict[str, int] = defaultdict(int)
    kilos: dict[str, float] = defaultdict(float)
    for f in facts:
        key = key_fn(f)
        if key is None:
            key = "unknown"
        counts[key] += 1
        kilos[key] += _kg(f.quantity, f.unit)
    rows = [{"label": k, "count": counts[k], "quantity_kg": round(kilos[k], 2)} for k in counts]
    rows.sort(key=lambda r: (r["count"], r["quantity_kg"]), reverse=True)
    return rows


def procurement_analytics(facts: list[ProcurementFact]) -> dict:
    """Village / crop / season splits + a monthly quantity trend (pure)."""
    by_village = _bucket(facts, lambda f: f.village)
    by_crop = _bucket(facts, lambda f: f.crop)

    def _season_key(f: ProcurementFact) -> str | None:
        d = _as_date(f.harvest_date)
        return _season(d) if d else None

    by_season = _bucket(facts, _season_key)

    trend: dict[str, float] = defaultdict(float)
    trend_count: dict[str, int] = defaultdict(int)
    for f in facts:
        d = _as_date(f.harvest_date)
        if d is None:
            continue
        label = d.strftime("%Y-%m")
        trend[label] += _kg(f.quantity, f.unit)
        trend_count[label] += 1
    quantity_trend = [
        {"label": label, "quantity_kg": round(trend[label], 2), "count": trend_count[label]}
        for label in sorted(trend)
    ]

    return {
        "by_village": by_village,
        "by_crop": by_crop,
        "by_season": by_season,
        "quantity_trend": quantity_trend,
        "total_offers": len(facts),
        "total_quantity_kg": round(sum(_kg(f.quantity, f.unit) for f in facts), 2),
    }
