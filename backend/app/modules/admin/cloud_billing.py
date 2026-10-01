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
    gross_spend_inr: float | None = None
    credits_inr: float | None = None
    gemini_spend_inr: float | None = None
    gemini_credits_inr: float | None = None


def _bigquery_timestamp(value: object) -> datetime:
    """BigQuery's REST API returns TIMESTAMP as epoch seconds ("1.7907192E9"),
    not ISO text; accept both (Sentry AGROWAI-BACKEND-5)."""
    text = str(value)
    try:
        return datetime.fromtimestamp(float(text), tz=UTC)
    except ValueError:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


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
              ,COALESCE(SUM(cost), 0) AS gross_spend
              ,COALESCE(SUM(IFNULL(
                (SELECT SUM(credit.amount) FROM UNNEST(credits) AS credit), 0
              )), 0) AS credits
              ,COALESCE(SUM(IF(
                REGEXP_CONTAINS(LOWER(CONCAT(service.description, ' ', sku.description)),
                  r'gemini|generative language|vertex ai'),
                cost + IFNULL((SELECT SUM(credit.amount) FROM UNNEST(credits) AS credit), 0),
                0
              )), 0) AS gemini_spend
              ,COALESCE(SUM(IF(
                REGEXP_CONTAINS(LOWER(CONCAT(service.description, ' ', sku.description)),
                  r'gemini|generative language|vertex ai'),
                IFNULL((SELECT SUM(credit.amount) FROM UNNEST(credits) AS credit), 0),
                0
              )), 0) AS gemini_credits
            FROM `{settings.gcp_billing_export_table}`
            WHERE project.id = @project_id
              AND usage_start_time >= TIMESTAMP(
                DATE_TRUNC(CURRENT_DATE('Asia/Kolkata'), MONTH), 'Asia/Kolkata'
              )
              AND usage_start_time < TIMESTAMP(
                DATE_ADD(
                  DATE_TRUNC(CURRENT_DATE('Asia/Kolkata'), MONTH), INTERVAL 1 MONTH
                ),
                'Asia/Kolkata'
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
        last_usage = _bigquery_timestamp(values[3]) if len(values) > 3 and values[3] else None
        gross_spend = float(values[4] or 0) if len(values) > 4 else None
        credits = float(values[5] or 0) if len(values) > 5 else None
        gemini_spend = float(values[6] or 0) if len(values) > 6 else None
        gemini_credits = float(values[7] or 0) if len(values) > 7 else None
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
            gross_spend_inr=round(gross_spend, 2) if gross_spend is not None else None,
            credits_inr=round(credits, 2) if credits is not None else None,
            gemini_spend_inr=round(gemini_spend, 2) if gemini_spend is not None else None,
            gemini_credits_inr=round(gemini_credits, 2) if gemini_credits is not None else None,
        )


cloud_billing_provider = CloudBillingProvider()
