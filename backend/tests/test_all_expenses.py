from datetime import UTC, datetime

import httpx
import pytest
from app.core.config import settings
from app.modules.admin.cloud_billing import CloudSpend
from app.modules.admin.openai_billing import OpenAIBillingProvider, OpenAISpend
from app.modules.admin.r2_billing import R2BillingProvider, R2Spend, _operation_class
from app.modules.admin.railway_billing import RailwaySpend
from app.modules.admin.service import AdminService

NOW = datetime(2026, 9, 11, tzinfo=UTC)


class CloudProvider:
    async def current_month_spend(self):
        return CloudSpend(
            "available", 1000, "INR", NOW, gemini_spend_inr=250, gemini_credits_inr=-50
        )


class RailwayProvider:
    async def current_usage(self):
        return RailwaySpend("available", 5, {"CPU_USAGE": 1.0})


class OpenAIProvider:
    async def current_month_spend(self):
        return OpenAISpend("available", 2)


class R2Provider:
    async def current_month_spend(self):
        return R2Spend("available", 1, 11, 1_000_001, 10_000_001)


def test_r2_operation_classes_are_explicit():
    assert _operation_class("PutObject") == "a"
    assert _operation_class("GetObject") == "b"
    assert _operation_class("DeleteObject") is None


class _FakeClient:
    def __init__(self, response: httpx.Response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, *args, **kwargs):
        return self.response

    async def post(self, *args, **kwargs):
        return self.response


@pytest.mark.asyncio
async def test_openai_cost_provider_sums_authoritative_cost_amounts(monkeypatch):
    request = httpx.Request("GET", "https://api.openai.com")
    response = httpx.Response(
        200,
        request=request,
        json={
            "data": [{"results": [{"amount": {"value": 1.25, "currency": "usd"}}]}],
            "has_more": False,
        },
    )
    monkeypatch.setattr(settings, "openai_admin_api_key", "test-admin-key")
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: _FakeClient(response))
    result = await OpenAIBillingProvider().current_month_spend()
    assert result.status == "available"
    assert result.spend_usd == 1.25


@pytest.mark.asyncio
async def test_r2_provider_applies_standard_free_tier(monkeypatch):
    request = httpx.Request("POST", "https://api.cloudflare.com")
    response = httpx.Response(
        200,
        request=request,
        json={
            "data": {
                "viewer": {
                    "accounts": [
                        {
                            "operations": [
                                {
                                    "sum": {"requests": 1_000_001},
                                    "dimensions": {
                                        "actionType": "PutObject",
                                        "bucketName": "photos",
                                    },
                                },
                                {
                                    "sum": {"requests": 10_000_001},
                                    "dimensions": {
                                        "actionType": "GetObject",
                                        "bucketName": "photos",
                                    },
                                },
                            ],
                            "storage": [],
                        }
                    ]
                }
            }
        },
    )
    monkeypatch.setattr(settings, "cloudflare_api_token", "test-token")
    monkeypatch.setattr(settings, "cloudflare_account_id", "test-account")
    monkeypatch.setattr(settings, "cloudflare_r2_bucket_names", ["photos"])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: _FakeClient(response))
    result = await R2BillingProvider().current_month_spend()
    assert result.status == "available"
    assert result.class_a_operations == 1_000_001
    assert result.class_b_operations == 10_000_001
    assert result.spend_usd == pytest.approx(0.000005)


@pytest.mark.asyncio
async def test_all_expenses_converts_once_and_does_not_double_count_gemini(db_session, monkeypatch):
    from tests.test_admin_flow import _admin_ctx

    monkeypatch.setattr(settings, "billing_usd_to_inr_rate", 80.0)
    service = AdminService(
        db_session,
        now=NOW,
        billing_provider=CloudProvider(),
        railway_provider=RailwayProvider(),
        openai_billing=OpenAIProvider(),
        r2_billing=R2Provider(),
    )
    ctx = await _admin_ctx(db_session, service)
    result = await service.all_expenses(ctx)
    assert result["total_monthly_inr"] == 1640.0
    assert result["total_is_complete"] is True
    gemini = next(row for row in result["providers"] if row["key"] == "gemini")
    assert gemini["amount"] == 250
    assert gemini["included_in_total"] is False


@pytest.mark.asyncio
async def test_all_expenses_never_claims_complete_when_fx_rate_missing(db_session, monkeypatch):
    from tests.test_admin_flow import _admin_ctx

    monkeypatch.setattr(settings, "billing_usd_to_inr_rate", 0.0)
    service = AdminService(
        db_session,
        now=NOW,
        billing_provider=CloudProvider(),
        railway_provider=RailwayProvider(),
        openai_billing=OpenAIProvider(),
        r2_billing=R2Provider(),
    )
    ctx = await _admin_ctx(db_session, service)
    result = await service.all_expenses(ctx)
    assert result["total_monthly_inr"] is None
    assert result["total_is_complete"] is False
