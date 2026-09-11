"""Estimated Cloudflare R2 month-to-date cost from Analytics API usage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("admin.r2_billing")
_GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"
_GIB = 1024**3


@dataclass(frozen=True)
class R2Spend:
    status: str
    spend_usd: float | None
    storage_gb_month: float | None
    class_a_operations: int | None
    class_b_operations: int | None
    message: str | None = None


def _operation_class(action: str) -> str | None:
    normalized = action.lower()
    if any(word in normalized for word in ("put", "create", "list", "copy", "complete", "upload")):
        return "a"
    if any(word in normalized for word in ("get", "head", "read")):
        return "b"
    return None  # deletes and unrecognised actions are not estimated


class R2BillingProvider:
    async def current_month_spend(self) -> R2Spend:
        if not settings.cloudflare_api_token or not settings.cloudflare_account_id:
            return R2Spend(
                "not_configured",
                None,
                None,
                None,
                None,
                "Cloudflare Analytics access is not configured.",
            )
        now = datetime.now(UTC)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        query = """query R2Costs($accountTag: string!, $start: Time!, $end: Time!) {
          viewer { accounts(filter: {accountTag: $accountTag}) {
            operations: r2OperationsAdaptiveGroups(
              limit: 10000, filter: {datetime_geq: $start, datetime_leq: $end}
            ) {
              sum { requests } dimensions { actionType bucketName }
            }
            storage: r2StorageAdaptiveGroups(
              limit: 10000
              filter: {datetime_geq: $start, datetime_leq: $end}
              orderBy: [datetime_DESC]
            ) {
              max { payloadSize metadataSize } dimensions { datetime bucketName }
            }
          }}
        }"""
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    _GRAPHQL_URL,
                    headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"},
                    json={
                        "query": query,
                        "variables": {
                            "accountTag": settings.cloudflare_account_id,
                            "start": start.isoformat().replace("+00:00", "Z"),
                            "end": now.isoformat().replace("+00:00", "Z"),
                        },
                    },
                )
            response.raise_for_status()
            body = response.json()
            if body.get("errors"):
                raise RuntimeError("Cloudflare GraphQL returned errors")
            accounts = body.get("data", {}).get("viewer", {}).get("accounts") or []
            if not accounts:
                raise RuntimeError("Cloudflare account analytics are unavailable")
            selected = set(settings.cloudflare_r2_bucket_names)
            operations = accounts[0].get("operations") or []
            storage = accounts[0].get("storage") or []
            class_a = class_b = 0
            for row in operations:
                dimensions = row.get("dimensions") or {}
                if selected and dimensions.get("bucketName") not in selected:
                    continue
                count = int((row.get("sum") or {}).get("requests") or 0)
                kind = _operation_class(str(dimensions.get("actionType") or ""))
                class_a += count if kind == "a" else 0
                class_b += count if kind == "b" else 0
            # One newest storage sample per bucket, prorated over elapsed month.
            latest: dict[str, tuple[str, float]] = {}
            for row in storage:
                dimensions = row.get("dimensions") or {}
                bucket = str(dimensions.get("bucketName") or "")
                if selected and bucket not in selected:
                    continue
                stamp = str(dimensions.get("datetime") or "")
                maximum = row.get("max") or {}
                size = float(maximum.get("payloadSize") or 0) + float(
                    maximum.get("metadataSize") or 0
                )
                if bucket not in latest or stamp > latest[bucket][0]:
                    latest[bucket] = (stamp, size)
            elapsed_fraction = max(1.0, (now - start).total_seconds() / 86400) / 30.0
            storage_gb_month = sum(size for _, size in latest.values()) / _GIB * elapsed_fraction
            # Standard R2 public rates/free tier. Estimate is deliberately unrounded internally.
            storage_cost = max(0.0, storage_gb_month - 10.0) * 0.015
            class_a_cost = max(0, class_a - 1_000_000) / 1_000_000 * 4.50
            class_b_cost = max(0, class_b - 10_000_000) / 1_000_000 * 0.36
            return R2Spend(
                "available",
                round(storage_cost + class_a_cost + class_b_cost, 6),
                round(storage_gb_month, 4),
                class_a,
                class_b,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Cloudflare R2 analytics query failed")
            return R2Spend(
                "unavailable",
                None,
                None,
                None,
                None,
                "Current R2 usage is temporarily unavailable.",
            )


r2_billing_provider = R2BillingProvider()
