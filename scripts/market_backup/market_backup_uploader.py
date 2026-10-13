"""AgrowNex market prices — plan 2 backup uploader (run on a computer in India).

Every night (Windows Task Scheduler, see install_task.ps1):
  1. Ask the backend how fresh its Tamil Nadu prices are (/market/sync-status).
  2. If they are fresh, stop.
  3. Otherwise download the official data.gov.in mandi records for the state
     (fallback: the Agmarknet 2.0 state report, which now needs a CAPTCHA) and
     upload them to /market/backup/ingest. The backend parses and validates
     them — only official per-quintal rows are stored.

Config: market_backup.env next to this file (never commit it):
    AGROWNEX_API_URL=https://api.agrowai.in/api/v1
    MARKET_INGEST_TOKEN=<same value as on Railway>
    DATA_GOV_API_KEY=<your data.gov.in API key>
Standard library only. Log: market_backup.log next to this file.
"""
from __future__ import annotations

import json
import logging
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGM2 = "https://api.agmarknet.gov.in/v1"
DATAGOV = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
DATAGOV_PAGE = 1000
DATAGOV_MAX_PAGES = 20
DATAGOV_FIELDS = ("state", "district", "market", "commodity", "variety", "grade",
                  "arrival_date", "min_price", "max_price", "modal_price")
STATE = "Tamil Nadu"
LOOKBACK_DAYS = 4
AGM_HEADERS = {
    "Accept": "application/json",
    "Referer": "https://agmarknet.gov.in/",
    "Origin": "https://agmarknet.gov.in",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36",
}
IST = timezone(timedelta(hours=5, minutes=30))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(HERE / "market_backup.log", encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("market-backup")


def load_config() -> dict[str, str]:
    cfg: dict[str, str] = {}
    path = HERE / "market_backup.env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                cfg[key.strip()] = value.strip()
    missing = [k for k in ("AGROWNEX_API_URL", "MARKET_INGEST_TOKEN") if not cfg.get(k)]
    if missing:
        sys.exit(f"market_backup.env is missing: {', '.join(missing)}")
    cfg["AGROWNEX_API_URL"] = cfg["AGROWNEX_API_URL"].rstrip("/")
    return cfg


def http_json(url: str, *, headers: dict[str, str], body: dict | None = None, timeout: int = 120):
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {**headers, **({"Content-Type": "application/json"} if data else {})}
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8", "replace"))


def backend_status(cfg: dict[str, str]) -> dict:
    url = f"{cfg['AGROWNEX_API_URL']}/market/sync-status?{urllib.parse.urlencode({'state': STATE})}"
    return http_json(url, headers={"Accept": "application/json"})["data"]


def _datagov_day(value: object) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value or "").strip(), fmt).date()
        except ValueError:
            continue
    return None


def fetch_datagov(api_key: str) -> tuple[date, list[dict]]:
    """Official data.gov.in mandi rows for STATE on the latest day it has."""
    rows: list[dict] = []
    for page in range(DATAGOV_MAX_PAGES):
        query = urllib.parse.urlencode({"api-key": api_key, "format": "json", "limit": DATAGOV_PAGE,
                                        "offset": page * DATAGOV_PAGE, "filters[state.keyword]": STATE})
        data = http_json(f"{DATAGOV}?{query}", headers={"Accept": "application/json"})
        batch = data.get("records") or []
        rows.extend(batch)
        if len(batch) < DATAGOV_PAGE or len(rows) >= int(data.get("total") or 0):
            break
    today = datetime.now(IST).date()
    days = {d for r in rows if (d := _datagov_day(r.get("arrival_date"))) and today - timedelta(days=LOOKBACK_DAYS) < d <= today}
    if not days:
        raise RuntimeError(f"data.gov.in has no {STATE} rows in the last {LOOKBACK_DAYS} days")
    day = max(days)
    records = [{k: r.get(k) for k in DATAGOV_FIELDS} for r in rows if _datagov_day(r.get("arrival_date")) == day]
    return day, records


def fetch_report() -> tuple[date, dict, dict[str, str]]:
    states = http_json(f"{AGM2}/location/state?page_size=100", headers=AGM_HEADERS)["states"]
    state_id = next(s["id"] for s in states if s["state_name"].strip().lower() == STATE.lower())
    districts = {
        r["market_name"]: r["district_name"]
        for r in http_json(f"{AGM2}/market-district-state", headers=AGM_HEADERS)
        if r.get("state_id") == state_id and r.get("market_name") and r.get("district_name")
    }
    today = datetime.now(IST).date()
    for back in range(LOOKBACK_DAYS):
        day = today - timedelta(days=back)
        query = urllib.parse.urlencode({"date": day.isoformat(), "stateIds": state_id, "includeExcel": "false"})
        try:
            report = http_json(f"{AGM2}/prices-and-arrivals/commodity-wise/daily-report-state?{query}",
                               headers=AGM_HEADERS)
        except urllib.error.HTTPError as exc:
            log.warning("Agmarknet 2.0 %s -> HTTP %s", day, exc.code)
            continue
        if report.get("markets"):
            return day, report, districts
        log.info("Agmarknet 2.0 %s: no reports yet", day)
    raise RuntimeError(f"No Agmarknet 2.0 report for {STATE} in the last {LOOKBACK_DAYS} days")


def main() -> int:
    cfg = load_config()
    force = "--force" in sys.argv
    try:
        status = backend_status(cfg)
        log.info("backend: latest=%s days_old=%s stale=%s sources=%s", status["latest_price_date"],
                 status["days_old"], status["stale"], status["sources_on_latest_date"])
        if not status["stale"] and (status["days_old"] or 0) <= 1 and not force:
            log.info("prices are fresh; nothing to do")
            return 0
    except Exception as exc:  # backend unreachable: still try to upload
        log.warning("could not read backend status: %s", exc)

    body: dict | None = None
    if cfg.get("DATA_GOV_API_KEY"):
        try:
            day, records = fetch_datagov(cfg["DATA_GOV_API_KEY"])
            log.info("downloaded data.gov.in %s: %s rows", day, len(records))
            body = {"state": STATE, "trade_day": day.isoformat(), "records": records}
        except Exception as exc:
            log.warning("data.gov.in download failed: %s", exc)
    else:
        log.warning("DATA_GOV_API_KEY not set in market_backup.env; trying Agmarknet 2.0 only")
    if body is None:
        try:
            day, report, districts = fetch_report()
        except Exception as exc:
            log.error("Agmarknet 2.0 download failed: %s", exc)
            return 2
        log.info("downloaded %s report: %s markets", day, len(report.get("markets") or []))
        body = {"state": STATE, "trade_day": day.isoformat(), "report": report, "districts": districts}

    try:
        result = http_json(
            f"{cfg['AGROWNEX_API_URL']}/market/backup/ingest",
            headers={"Accept": "application/json", "X-Market-Ingest-Token": cfg["MARKET_INGEST_TOKEN"]},
            body=body,
            timeout=180,
        )
    except urllib.error.HTTPError as exc:
        log.error("upload failed: HTTP %s %s", exc.code, exc.read()[:300])
        return 3
    except Exception as exc:
        log.error("upload failed: %s", exc)
        return 3
    log.info("uploaded: %s", result.get("data"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
