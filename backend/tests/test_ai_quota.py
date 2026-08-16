"""Per-farmer daily AI quota tests (Phase 2 — protect the Gemini budget)."""
from __future__ import annotations

import pytest
from app.core.config import settings
from app.core.exceptions import QuotaExceededError
from app.modules.ai.provider import AIResult
from app.modules.ai.schemas import ChatRequest
from app.modules.ai.service import AIService
from app.modules.auth.models import User


class ChatProvider:
    model = "gemini-2.5-flash"

    async def generate(self, *, system, history, message) -> AIResult:
        return AIResult(text="ok", model="gemini-2.5-flash", input_tokens=10, output_tokens=10)


async def _user(db_session, uid: str = "fb-quota-1") -> User:
    user = User(firebase_uid=uid, phone_number="+919000000009", status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def test_chat_blocks_when_daily_quota_reached(
    db_session, session_factory, monkeypatch
):
    monkeypatch.setattr("app.modules.ai.usage_ledger.SessionLocal", session_factory)
    monkeypatch.setattr(settings, "ai_daily_chat_quota", 1)
    service = AIService(db_session, provider=ChatProvider())
    user = await _user(db_session)

    # First chat is allowed (records one usage row).
    await service.chat(user, ChatRequest(message="first"))
    # Second chat in the same day is over quota.
    with pytest.raises(QuotaExceededError):
        await service.chat(user, ChatRequest(message="second"))
