"""Tests for the rule-pack directory loader (registry.py).

Separate from test_disease_risk_engine.py (which tests RulePackRegistry's own
activation/hash/status logic using in-memory RulePack instances) -- this
covers the filesystem loading + parsing steps: which files get picked up,
and that a bad file degrades gracefully instead of crashing app startup.
Mirrors tests/test_calendar_registry_loader.py for the calendar module.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.modules.disease_risk.registry import (
    _load_rule_pack_entries,
    _parse_rule_pack_entries,
)


def test_missing_directory_returns_empty(tmp_path: Path) -> None:
    assert _load_rule_pack_entries(tmp_path / "does_not_exist") == []


def test_loads_json_files_as_raw_dicts(tmp_path: Path) -> None:
    (tmp_path / "paddy_blast.json").write_text(json.dumps({"pack_id": "paddy-blast"}))
    (tmp_path / "cotton_wilt.json").write_text(json.dumps({"pack_id": "cotton-wilt"}))

    entries = _load_rule_pack_entries(tmp_path)

    assert {e["pack_id"] for e in entries} == {"paddy-blast", "cotton-wilt"}


def test_ignores_non_json_files(tmp_path: Path) -> None:
    (tmp_path / "_TEMPLATE.json.example").write_text(json.dumps({"pack_id": "template"}))
    (tmp_path / "README.md").write_text("not a rule pack")

    assert _load_rule_pack_entries(tmp_path) == []


def test_skips_malformed_json_without_raising(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{not valid json")
    (tmp_path / "paddy_blast.json").write_text(json.dumps({"pack_id": "paddy-blast"}))

    entries = _load_rule_pack_entries(tmp_path)

    assert len(entries) == 1
    assert entries[0]["pack_id"] == "paddy-blast"


def test_skips_non_object_json_without_raising(tmp_path: Path) -> None:
    (tmp_path / "list.json").write_text(json.dumps(["not", "an", "object"]))

    assert _load_rule_pack_entries(tmp_path) == []


def test_parse_skips_schema_invalid_entries_without_raising() -> None:
    valid_raw = {
        "schema_version": "1.0",
        "pack_id": "paddy-blast-tn",
        "version": "1.0.0",
        "crop_id": "paddy",
        "disease_id": "blast",
        "regions": ["IN-TN"],
        "seasons": ["kharif"],
        "confirmed_stages": ["tillering"],
        "required_weather_variables": ["humidity_pct"],
        "observation_window_hours": 24,
        "forecast_window_hours": 48,
        "conditions": [{"variable": "humidity_pct", "operator": "gte", "value": 90}],
        "minimum_data_completeness": 1.0,
        "maximum_weather_age_hours": 6,
        "cached_weather_allowed": False,
        "alert_title_key": "diseaseRisk.verified.paddy_blast.title",
        "alert_explanation_key": "diseaseRisk.verified.paddy_blast.explanation",
        "source_references": ["test:reference"],
        "reviewer_id": "test-reviewer",
        "approval_status": "UNVERIFIED",
        "approved_at": None,
        "review_expires_at": "2027-01-01T00:00:00Z",
        "cooldown_hours": 24,
        "alert_expiry_hours": 12,
        "content_hash": "0" * 64,
    }
    invalid_raw = {"pack_id": "missing-everything-else"}

    parsed = _parse_rule_pack_entries([valid_raw, invalid_raw])

    assert len(parsed) == 1
    assert parsed[0].pack_id == "paddy-blast-tn"
