"""Regression: every verified schedule's document_reference must fit the
crop_calendar_events.registry_source_reference column (Sentry AGROWAI-BACKEND-C)."""

import json
from pathlib import Path

from sqlalchemy import Text

from app.modules.calendar.models import CalendarEvent

SCHEDULES = Path(__file__).resolve().parents[1] / "app/modules/calendar/data/verified_schedules"


def test_source_reference_column_fits_all_verified_schedules():
    column = CalendarEvent.__table__.c.registry_source_reference
    limit = getattr(column.type, "length", None)
    longest = max(
        len(json.loads(p.read_text(encoding="utf-8")).get("document_reference", ""))
        for p in SCHEDULES.glob("*.json")
    )
    assert isinstance(column.type, Text) or (limit is not None and longest <= limit), (
        f"registry_source_reference ({column.type}) too short for {longest}-char reference"
    )
