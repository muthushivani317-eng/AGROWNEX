"""OpenAI organization month-to-date costs (server-side only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("admin.openai_billing")
_COSTS_URL = "https://api.openai.com/v1/organization/costs"


@dataclass(frozen=True)
class OpenAISpend:
    status: str
    spend_usd: float | None
    message: str | None = None


class OpenAIBillingProvider:
    async def current_month_spend(self) -> OpenAISpend:
        api_key = settings.openai_admin_api_key or settings.openai_vision_diagnosis_api_key
        if not api_key:
            return OpenAISpend("not_configured", None, "OpenAI billing access is not configured.")
        now = datetime.now(UTC)
        start = int(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())
        end = int(now.timestamp()) + 1
        headers = {"Authorization": f"Bearer {api_key}"}
        if settings.openai_organization_id:
            headers["OpenAI-Organization"] = settings.openai_organization_id
        total = 0.0
        page: str | None = None
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                while True:
                    params: dict[str, str | int] = {
                        "start_time": start,
                        "end_time": end,
                        "bucket_width": "1d",
                        "limit": 31,
                    }
                    if page:
                        params["page"] = page
                    response = await client.get(_COSTS_URL, headers=headers, params=params)
                    if response.status_code in {401, 403}:
                        return OpenAISpend(
                            "unavailable",
                            None,
                            "OpenAI organization costs require an Admin API key.",
                        )
                    response.raise_for_status()
                    body = response.json()
                    for bucket in body.get("data", []):
                        for result in bucket.get("results", []):
                            amount = result.get("amount") or {}
                            if str(amount.get("currency", "")).lower() != "usd":
                                raise RuntimeError("OpenAI costs returned a non-USD currency")
                            total += float(amount.get("value") or 0)
                    if not body.get("has_more"):
                        break
                    page = body.get("next_page")
                    if not page:
                        raise RuntimeError("OpenAI costs pagination cursor is missing")
            return OpenAISpend("available", round(total, 4))
        except Exception:  # noqa: BLE001
            logger.exception("OpenAI organization costs query failed")
            return OpenAISpend(
                "unavailable", None, "Current OpenAI costs are temporarily unavailable."
            )


openai_billing_provider = OpenAIBillingProvider()
