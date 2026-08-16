"""Shared India Standard Time helpers.

Timestamps that record *when something happened* (created_at, completed_at,
audit/login logs, token expiry, etc.) should stay UTC everywhere in this
codebase, matching standard practice and how they're already stored. This
module is only for the different question: "what calendar day is it today,
for the farmer" -- day-boundary checks, "today's" filters, N-days-back
history windows.

Before this module existed, several places answered that question with a
plain ``datetime.now(UTC).date()``. Since India is UTC+5:30 with no
half-hour-aligned DST, that still returns *yesterday's* date for the ~5.5
hours between local midnight and 05:30 IST. Concretely this meant
``/calendar/today`` showed yesterday's tasks as "today's" (and hid the
actual day's tasks), ``/calendar/missed`` under-reported missed tasks,
``produce``'s harvest-date validation and "upcoming" bucketing were off by
the same margin, and ``market``'s ``today_only`` filter and history window
start date were both wrong -- every night, for an India-only app (found in
the 2026-08 pre-release audit). Use ``today_ist()``/``now_ist()`` for any
new "as of today" logic instead of ``datetime.now(UTC)``.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    """Current time in India Standard Time (timezone-aware)."""
    return datetime.now(UTC).astimezone(IST)


def today_ist() -> date:
    """Today's calendar date in India Standard Time."""
    return now_ist().date()
