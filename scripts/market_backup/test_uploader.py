"""Uploader decision logic (no network): skip when fresh, upload when stale."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture()
def up(tmp_path, monkeypatch):
    import market_backup_uploader as module

    module = importlib.reload(module)
    monkeypatch.setattr(module, "load_config", lambda: {"AGROWNEX_API_URL": "https://api.x/api/v1",
                                                         "MARKET_INGEST_TOKEN": "t"})
    return module


def _fake_http(calls, status):
    def http_json(url, *, headers, body=None, timeout=120):
        calls.append((url, body is not None, headers.get("X-Market-Ingest-Token")))
        if "sync-status" in url:
            return {"data": status}
        if "location/state" in url:
            return {"states": [{"id": 31, "state_name": "Tamil Nadu"}]}
        if "market-district-state" in url:
            return [{"state_id": 31, "market_name": "Kallakurichi APMC", "district_name": "Kallakurichi"},
                    {"state_id": 2, "market_name": "Other", "district_name": "X"}]
        if "daily-report-state" in url:
            return {"markets": [{"marketName": "Kallakurichi APMC"}]}
        if url.endswith("/market/backup/ingest"):
            assert body["state"] == "Tamil Nadu"
            assert body["districts"] == {"Kallakurichi APMC": "Kallakurichi"}
            return {"data": {"saved": 1}}
        raise AssertionError(url)
    return http_json


def test_skips_when_backend_is_fresh(up, monkeypatch):
    calls = []
    monkeypatch.setattr(up, "http_json", _fake_http(calls, {"latest_price_date": "2026-09-30", "days_old": 1,
                                                            "stale": False, "sources_on_latest_date": []}))
    assert up.main() == 0
    assert len(calls) == 1  # status only


def test_uploads_official_report_when_stale(up, monkeypatch):
    calls = []
    monkeypatch.setattr(up, "http_json", _fake_http(calls, {"latest_price_date": None, "days_old": None,
                                                            "stale": True, "sources_on_latest_date": []}))
    assert up.main() == 0
    upload = calls[-1]
    assert upload[0].endswith("/market/backup/ingest") and upload[1] and upload[2] == "t"
