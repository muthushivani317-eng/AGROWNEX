"""Railway current resource usage via the public GraphQL API."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("admin.railway_billing")
GRAPHQL_URL = "https://backboard.railway.com/graphql/v2"
USD_RATES = {
    "CPU_USAGE": 20.0 / 43_200,
    "MEMORY_USAGE_GB": 10.0 / 43_200,
    "NETWORK_TX_GB": 0.05,
    "DISK_USAGE_GB": 0.15 / 43_200,
    "BACKUP_USAGE_GB": 0.15 / 43_200,
}


@dataclass(frozen=True)
class RailwaySpend:
    status: str
    spend_usd: float | None
    breakdown_usd: dict[str, float]
    message: str | None = None


class RailwayBillingProvider:
    async def current_usage(self) -> RailwaySpend:
        if not all((settings.railway_api_token, settings.railway_workspace_id,
                    settings.railway_project_id)):
            return RailwaySpend("not_configured", None, {}, "Railway usage is not configured.")
        query = """query Usage($workspaceId: String!, $projectId: String!) {
          usage(workspaceId: $workspaceId, projectId: $projectId,
            measurements: [CPU_USAGE, MEMORY_USAGE_GB, NETWORK_TX_GB,
              DISK_USAGE_GB, BACKUP_USAGE_GB]) { measurement value }
        }"""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    GRAPHQL_URL,
                    headers={"Authorization": f"Bearer {settings.railway_api_token}"},
                    json={"query": query, "variables": {
                        "workspaceId": settings.railway_workspace_id,
                        "projectId": settings.railway_project_id,
                    }},
                )
            response.raise_for_status()
            body = response.json()
            if body.get("errors"):
                raise RuntimeError("Railway GraphQL returned errors")
            rows = body.get("data", {}).get("usage")
            if not isinstance(rows, list):
                raise RuntimeError("Railway usage response is malformed")
            breakdown = {
                row["measurement"]: round(float(row["value"]) * USD_RATES[row["measurement"]], 4)
                for row in rows if row.get("measurement") in USD_RATES
            }
            return RailwaySpend("available", round(sum(breakdown.values()), 2), breakdown)
        except Exception:  # noqa: BLE001
            logger.exception("Railway usage query failed")
            return RailwaySpend("unavailable", None, {},
                                "Current Railway usage is temporarily unavailable.")


railway_billing_provider = RailwayBillingProvider()
