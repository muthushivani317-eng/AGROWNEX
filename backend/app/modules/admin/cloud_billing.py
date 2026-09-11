"""Read actual GCP month-to-date spend from Cloud Billing BigQuery export.

The Cloud Billing Budgets API exposes budget configuration, not accrued spend.
Actual cost therefore comes from the detailed billing export. Credentials stay
server-side and must have BigQuery Job User plus read access to the export table.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("admin.cloud_billing")

_TABLE_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+$")
_BIGQUERY_SCOPE = "https://www.googleapis.com/auth/bigquery.readonly"


@dataclass(frozen=True)
class CloudSpend:
    status: str
    spend_inr: float | None
    currency: str | None
    last_usage_at: datetime | None
    message: str | None = None


class CloudBillingProvider:
    async def current_month_spend(self) -> CloudSpend:
        if not settings.gcp_billing_project_id or not settings.gcp_billing_export_table:
            return CloudSpend(
                status="not_configured",
                spend_inr=None,
                currency=None,
                last_usage_at=None,
                message="Cloud Billing export is not configured.",
            )
        if not _TABLE_RE.fullmatch(settings.gcp_billing_export_table):
            logger.error("invalid GCP billing export table identifier")
            return CloudSpend(
                status="unavailable",
                spend_inr=None,
                currency=None,
                last_usage_at=None,
                message="Cloud Billing export configuration is invalid.",
            )
        try:
            return await asyncio.to_thread(self._query)
        except Exception:  # noqa: BLE001 - admin dashboard must degrade safely
            logger.exception("GCP billing query failed")
            return CloudSpend(
                status="unavailable",
                spend_inr=None,
                currency=None,
                last_usage_at=None,
                message="Current GCP billing data is temporarily unavailable.",
            )

    def _credentials(self):
        import google.auth
        from google.oauth2 import service_account

        if settings.firebase_credentials_json:
            info = json.loads(settings.firebase_credentials_json)
            return service_account.Credentials.from_service_account_info(
                info, scopes=[_BIGQUERY_SCOPE]
            )
        credentials, _ = google.auth.default(scopes=[_BIGQUERY_SCOPE])
        return credentials

    def _query(self) -> CloudSpend:
        from google.auth.transport.requests import AuthorizedSession

        query_project = settings.gcp_billing_query_project_id or settings.gcp_billing_project_id
        sql = f"""
            SELECT
              COALESCE(SUM(cost + IFNULL(
                (SELECT SUM(credit.amount) FROM UNNEST(credits) AS credit), 0
              )), 0) AS spend,
              ANY_VALUE(currency) AS currency,
              COUNT(DISTINCT currency) AS currency_count,
              MAX(usage_start_time) AS last_usage_at
            FROM `{settings.gcp_billing_export_table}`
            WHERE project.id = @project_id
              AND usage_start_time >= TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), MONTH, 'Asia/Kolkata')
              AND usage_start_time < TIMESTAMP_ADD(
                TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), MONTH, 'Asia/Kolkata'), INTERVAL 1 MONTH
              )
        """
        payload: dict[str, Any] = {
            "query": sql,
            "useLegacySql": False,
            "timeoutMs": 15000,
            "location": settings.gcp_billing_location,
            "parameterMode": "NAMED",
            "queryParameters": [
                {
                    "name": "project_id",
                    "parameterType": {"type": "STRING"},
                    "parameterValue": {"value": settings.gcp_billing_project_id},
                }
            ],
        }
        response = AuthorizedSession(self._credentials()).post(
            f"https://bigquery.googleapis.com/bigquery/v2/projects/{query_project}/queries",
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("jobComplete", False):
            raise RuntimeError("BigQuery billing query did not complete within the timeout")
        rows = body.get("rows") or []
        values = [cell.get("v") for cell in rows[0].get("f", [])] if rows else []
        spend = float(values[0] or 0) if values else 0.0
        currency = str(values[1]) if len(values) > 1 and values[1] else None
        currency_count = int(values[2] or 0) if len(values) > 2 else 0
        last_usage = (
            datetime.fromisoformat(str(values[3]).replace("Z", "+00:00")).astimezone(UTC)
            if len(values) > 3 and values[3]
            else None
        )
        if currency_count > 1 or (currency and currency != "INR"):
            return CloudSpend(
                status="unavailable",
                spend_inr=None,
                currency=currency,
                last_usage_at=last_usage,
                message="Billing export currency is not INR; budget comparison is disabled.",
            )
        return CloudSpend(
            status="available",
            spend_inr=round(spend, 2),
            currency=currency or "INR",
            last_usage_at=last_usage,
        )


cloud_billing_provider = CloudBillingProvider()
