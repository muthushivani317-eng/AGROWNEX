"""Check both price sources from a computer in India (no install needed).

    python relay/check_sources.py                   # direct: Agmarknet 2.0 (+ data.gov.in if DATA_GOV_API_KEY set)
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

AGM2 = "https://api.agmarknet.gov.in/v1"
DATA_GOV_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
HEADERS = {
    "Accept": "application/json",
    "Referer": "https://agmarknet.gov.in/",
    "Origin": "https://agmarknet.gov.in",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36",
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
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.loads(res.read().decode("utf-8", "replace"))


def check_agmarknet_v2(relay) -> None:
    states = _send("GET", f"{AGM2}/location/state?page_size=100", None, HEADERS, relay)["states"]
    sid = next(s["id"] for s in states if s["state_name"].lower() == "tamil nadu")
    for back in range(1, 5):
        day = (date.today() - timedelta(days=back)).isoformat()
        query = urllib.parse.urlencode({"date": day, "stateIds": sid, "includeExcel": "false"})
        data = _send("GET", f"{AGM2}/prices-and-arrivals/commodity-wise/daily-report-state?{query}",
                     None, HEADERS, relay)
        markets = data.get("markets") or []
        rows = sum(len(c.get("data") or []) for m in markets for g in m.get("commodityGroups") or []
                   for c in g.get("commodities") or [])
        if rows:
            print(f"Agmarknet 2.0 OK - {day}: {len(markets)} markets, {rows} price rows")
            return
        print(f"Agmarknet 2.0    - {day}: no reports, trying the day before")
    print("Agmarknet 2.0 reachable but no Tamil Nadu reports in the last 4 days")


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
    for check in (check_agmarknet_v2, check_data_gov):
        try:
            check(relay)
        except Exception as exc:  # report and continue with the next source
            print(f"{check.__name__.removeprefix('check_')} FAILED: {type(exc).__name__}: {exc}")
