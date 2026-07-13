"""Tests for AI token-usage recording + the admin cost dashboard (Phase 1)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.modules.admin.constants import AdminRole
from app.modules.admin.seed import ensure_admin
from app.modules.admin.service import AdminService
from app.modules.ai.constants import estimate_cost_inr
from app.modules.ai.models import TokenUsage
from app.modules.ai.provider import AIResult
from app.modules.ai.repositories import TokenUsageRepository
from app.modules.ai.schemas import ChatRequest
from app.modules.ai.service import AIService
from app.modules.auth.models import User
from sqlalchemy import func, select


class UsageProvider:
    """Fake chat provider that reports token usage (like a real Gemini call)."""

    def __init__(self) -> None:
        self.model = "gemini-2.5-flash"

    async def generate(self, *, system, history, message) -> AIResult:
        return AIResult(
            text=f"Echo: {message}",
            model="gemini-2.5-flash",
            input_tokens=1000,
            output_tokens=1000,
            latency_ms=123,
            provider="gemini",
        )


async def _user(db_session, uid: str = "fb-cost-1") -> User:
    user = User(firebase_uid=uid, phone_number="+919000000001", status="active")
    db_session.add(user)
    await db_session.flush()
    return user


# --------------------------------------------------------------------------- #
# Cost table
# --------------------------------------------------------------------------- #
def test_estimate_cost_is_zero_when_tokens_unknown():
    assert estimate_cost_inr("gemini-2.5-flash", None, None) == 0.0


def test_flash_is_cheaper_than_pro_for_same_tokens():
    flash = estimate_cost_inr("gemini-2.5-flash", 1000, 1000)
    pro = estimate_cost_inr("gemini-2.5-pro", 1000, 1000)
    assert 0 < flash < pro


# --------------------------------------------------------------------------- #
# Recording
# --------------------------------------------------------------------------- #
async def test_chat_records_token_usage(db_session):
    service = AIService(db_session, provider=UsageProvider())
    user = await _user(db_session)

    await service.chat(user, ChatRequest(message="How do I grow paddy?"))

    rows = (await db_session.execute(select(TokenUsage))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.module == "ai_chat"
    assert row.model == "gemini-2.5-flash"
    assert row.farmer_id == user.id
    assert row.input_tokens == 1000
    assert row.output_tokens == 1000
    assert row.estimated_cost_inr == estimate_cost_inr("gemini-2.5-flash", 1000, 1000)
    assert row.is_sample is False


async def test_record_with_unknown_tokens_costs_zero(db_session):
    repo = TokenUsageRepository(db_session)
    row = await repo.record(
        farmer_id=None,
        module="disease",
        model="mock-gemini-vision",
        input_tokens=None,
        output_tokens=None,
        latency_ms=None,
        provider="mock",
        is_sample=True,
    )
    assert row.estimated_cost_inr == 0.0
    assert row.is_sample is True


# --------------------------------------------------------------------------- #
# Aggregation via the admin cost dashboard
# --------------------------------------------------------------------------- #
async def _seed_usage(db_session) -> None:
    repo = TokenUsageRepository(db_session)
    # Two flash chat calls + one pro disease call.
    await repo.record(
        farmer_id=None, module="ai_chat", model="gemini-2.5-flash",
        input_tokens=1000, output_tokens=1000, latency_ms=100,
    )
    await repo.record(
        farmer_id=None, module="ai_chat", model="gemini-2.5-flash",
        input_tokens=2000, output_tokens=500, latency_ms=110,
    )
    await repo.record(
        farmer_id=None, module="disease", model="gemini-2.5-pro",
        input_tokens=800, output_tokens=1200, latency_ms=900,
    )


async def _admin(db_session, service: AdminService):
    user = await _user(db_session, uid=f"fb-admin-{uuid.uuid4().hex[:6]}")
    await ensure_admin(db_session, user.id, role=AdminRole.SUPER_ADMIN.value, full_name="Ops")
    return await service.resolve_admin(user)


async def test_ai_costs_aggregates_by_model_and_module(db_session):
    await _seed_usage(db_session)
    service = AdminService(db_session)
    ctx = await _admin(db_session, service)

    data = await service.ai_costs(ctx, window_days=30)

    assert data["total_requests"] == 3
    by_model = {r.key: r for r in data["by_model"]}
    assert by_model["gemini-2.5-flash"].requests == 2
    assert by_model["gemini-2.5-pro"].requests == 1
    by_module = {r.key: r for r in data["by_module"]}
    assert by_module["ai_chat"].requests == 2
    assert by_module["disease"].requests == 1
    # Totals reconcile across the two groupings.
    assert round(sum(r.cost_inr for r in data["by_model"]), 6) == data["total_cost_inr"]
    assert round(sum(r.cost_inr for r in data["by_module"]), 6) == data["total_cost_inr"]
    assert data["daily"]  # at least one day bucket present


async def test_ai_costs_window_excludes_older_rows(db_session):
    # One recent row (via repo) + one 60-day-old row (inserted directly).
    repo = TokenUsageRepository(db_session)
    await repo.record(
        farmer_id=None, module="ai_chat", model="gemini-2.5-flash",
        input_tokens=1000, output_tokens=1000, latency_ms=100,
    )
    old = TokenUsage(
        module="ai_chat", model="gemini-2.5-flash", provider="gemini",
        input_tokens=1000, output_tokens=1000, latency_ms=100,
        estimated_cost_inr=estimate_cost_inr("gemini-2.5-flash", 1000, 1000),
        created_at=datetime.now(UTC) - timedelta(days=60),
    )
    db_session.add(old)
    await db_session.flush()

    service = AdminService(db_session)
    ctx = await _admin(db_session, service)

    data = await service.ai_costs(ctx, window_days=30)
    assert data["total_requests"] == 1  # the 60-day-old row is excluded

    total_rows = (
        await db_session.execute(select(func.count()).select_from(TokenUsage))
    ).scalar_one()
    assert total_rows == 2  # both rows persisted; only the window is filtered
