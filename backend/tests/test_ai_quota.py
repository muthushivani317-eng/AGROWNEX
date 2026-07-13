"""Per-farmer daily AI quota tests (Phase 2 — protect the Gemini budget)."""
from __future__ import annotations

import base64

import pytest
from app.core.config import settings
from app.core.exceptions import QuotaExceededError
from app.modules.ai.provider import AIResult
from app.modules.ai.schemas import ChatRequest
from app.modules.ai.service import AIService
from app.modules.auth.models import User
from app.modules.disease import service as disease_service_module
from app.modules.disease.quality import QualityResult
from app.modules.disease.schemas import AnalyzeRequest
from app.modules.disease.service import DiseaseService
from app.modules.disease.storage import MockStorage

from tests.test_disease_flow import FakeProvider as DiseaseFakeProvider
from tests.test_disease_flow import make_analysis


class ChatProvider:
    model = "gemini-2.5-flash"

    async def generate(self, *, system, history, message) -> AIResult:
        return AIResult(text="ok", model="gemini-2.5-flash", input_tokens=10, output_tokens=10)


async def _user(db_session, uid: str = "fb-quota-1") -> User:
    user = User(firebase_uid=uid, phone_number="+919000000009", status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def test_chat_blocks_when_daily_quota_reached(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ai_daily_chat_quota", 1)
    service = AIService(db_session, provider=ChatProvider())
    user = await _user(db_session)

    # First chat is allowed (records one usage row).
    await service.chat(user, ChatRequest(message="first"))
    # Second chat in the same day is over quota.
    with pytest.raises(QuotaExceededError):
        await service.chat(user, ChatRequest(message="second"))


async def test_disease_blocks_when_daily_quota_reached(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ai_daily_disease_quota", 1)
    monkeypatch.setattr(
        disease_service_module, "assess_quality", lambda _m: QualityResult(True, [])
    )
    provider = DiseaseFakeProvider(make_analysis())
    service = DiseaseService(db_session, provider=provider, storage=MockStorage())
    user = await _user(db_session, uid="fb-quota-2")

    img = base64.b64encode(b"\x00" * 64).decode()
    await service.analyze(user, AnalyzeRequest(image_base64=img, mime_type="image/jpeg"))
    with pytest.raises(QuotaExceededError):
        await service.analyze(
            user, AnalyzeRequest(image_base64=img, mime_type="image/jpeg")
        )
