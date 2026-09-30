"""Check both price sources from a computer in India (no install needed).

    python relay/check_sources.py                   # direct: eNAM (+ data.gov.in if DATA_GOV_API_KEY set)
    python relay/check_sources.py --relay URL TOKEN # same, but through the deployed relay

Prints how many Tamil Nadu price rows each source returned. Standard library only.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

ENAM_URL = "https://enam.gov.in/web/Ajax_ctrl/trade_data_list"
DATA_GOV_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://enam.gov.in/web/dashboard/trade-data",
    "Origin": "https://enam.gov.in",
    "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36",
}


def _send(method: str, url: str, body: bytes | None, headers: dict, relay: tuple[str, str] | None):
    if relay:
        relay_url, token = relay
        payload = json.dumps({
            "method": method,
            "url": url,
            "headers": headers,
            "body_b64": base64.b64encode(body).decode() if body else None,
        }).encode()
        req = urllib.request.Request(
            relay_url.rstrip("/") + "/fetch",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        )
    else:
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=90) as res:
        return json.loads(res.read().decode("utf-8", "replace"))


def check_enam(relay) -> None:
    for back in range(5):
        day = (date.today() - timedelta(days=back)).isoformat()
        form = urllib.parse.urlencode({
            "language": "en", "stateName": "TAMIL NADU", "apmcName": "-- Select APMCs --",
            "commodityName": "-- Select Commodity --", "fromDate": day, "toDate": day,
        }).encode()
        headers = {**HEADERS, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        data = _send("POST", ENAM_URL, form, headers, relay)
        rows = data.get("data", []) if isinstance(data, dict) else data
        if rows:
            print(f"eNAM OK  - {day}: {len(rows)} rows. Sample: {json.dumps(rows[0])[:300]}")
            return
        print(f"eNAM     - {day}: no trades, trying the day before")
    print("eNAM reachable but no Tamil Nadu trades in the last 5 days")


def check_data_gov(relay) -> None:
    key = os.getenv("DATA_GOV_API_KEY", "")
    if not key:
        print("data.gov.in skipped (set DATA_GOV_API_KEY to test it)")
        return
    query = urllib.parse.urlencode(
        {"api-key": key, "format": "json", "limit": 10, "filters[state]": "Tamil Nadu"}
    )
    data = _send("GET", f"{DATA_GOV_URL}?{query}", None, {"Accept": "application/json"}, relay)
    print(f"data.gov.in OK - {len(data.get('records', []))} rows (total {data.get('total')})")


if __name__ == "__main__":
    relay = (sys.argv[2], sys.argv[3]) if len(sys.argv) == 4 and sys.argv[1] == "--relay" else None
    print("Checking through relay" if relay else "Checking directly from this computer")
    for check in (check_enam, check_data_gov):
        try:
            check(relay)
        except Exception as exc:  # report and continue with the next source
            print(f"{check.__name__.removeprefix('check_')} FAILED: {type(exc).__name__}: {exc}")
