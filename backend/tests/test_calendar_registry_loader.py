"""Tests for the verified-schedule directory loader (registry.py).

Separate from test_calendar_registry.py (which tests CropStageRegistry's own
validation/hash/status logic using in-memory entries) -- this covers the
filesystem loading step: which files get picked up, and that a bad file
degrades gracefully instead of crashing app startup.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.modules.calendar.registry import _load_verified_schedule_entries


def test_missing_directory_returns_empty(tmp_path: Path) -> None:
    assert _load_verified_schedule_entries(tmp_path / "does_not_exist") == []


def test_loads_json_files_as_raw_dicts(tmp_path: Path) -> None:
    (tmp_path / "paddy.json").write_text(json.dumps({"canonical_crop_id": "paddy"}))
    (tmp_path / "maize.json").write_text(json.dumps({"canonical_crop_id": "maize"}))

    entries = _load_verified_schedule_entries(tmp_path)

    assert {e["canonical_crop_id"] for e in entries} == {"paddy", "maize"}


def test_ignores_non_json_files(tmp_path: Path) -> None:
    (tmp_path / "_TEMPLATE.json.example").write_text(
        json.dumps({"canonical_crop_id": "template"})
    )
    (tmp_path / "README.md").write_text("not a schedule")

    assert _load_verified_schedule_entries(tmp_path) == []


def test_skips_malformed_json_without_raising(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{not valid json")
    (tmp_path / "paddy.json").write_text(json.dumps({"canonical_crop_id": "paddy"}))

    entries = _load_verified_schedule_entries(tmp_path)

    assert len(entries) == 1
    assert entries[0]["canonical_crop_id"] == "paddy"


def test_skips_non_object_json_without_raising(tmp_path: Path) -> None:
    (tmp_path / "list.json").write_text(json.dumps(["not", "an", "object"]))

    assert _load_verified_schedule_entries(tmp_path) == []
