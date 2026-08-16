"""Read-time weather advisories for calendar tasks (docs: reuse Weather module).

This module NEVER computes weather itself. It consumes the deterministic insight
codes already produced by ``app.modules.weather.insights`` and maps them onto a
task's weather dependency:

    heavy rain  + irrigation task → delay irrigation
    strong wind + spraying task   → delay spraying
    extreme heat + irrigation task → recommend irrigation

The stored scheduled date is never mutated — the advisory is an annotation the
frontend renders (Tamil-first) and future AI can act on.
"""

from __future__ import annotations

from app.modules.calendar.constants import WeatherAdvisory, WeatherDependency
from app.modules.weather.schemas import WeatherBundle, WeatherInsight


def collect_insight_codes(insights: list[WeatherInsight]) -> set[str]:
    return {insight.code for insight in insights}


def codes_from_bundle(bundle: WeatherBundle | None) -> set[str]:
    if bundle is None:
        return set()
    return collect_insight_codes(bundle.insights)


def _has_prefix(codes: set[str], prefix: str) -> bool:
    return any(code.startswith(prefix) for code in codes)


def advisory_for(dependency: WeatherDependency, codes: set[str]) -> WeatherAdvisory:
    """Map reused weather insight codes to an advisory for one task."""
    if dependency == WeatherDependency.IRRIGATION:
        if _has_prefix(codes, "heavy_rain."):
            return WeatherAdvisory.DELAY_IRRIGATION
        if _has_prefix(codes, "heat_stress."):
            return WeatherAdvisory.RECOMMEND_IRRIGATION
    elif dependency == WeatherDependency.SPRAYING:
        if "wind.strong" in codes:
            return WeatherAdvisory.DELAY_SPRAYING
    return WeatherAdvisory.NONE
