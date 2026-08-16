from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.ai.service import AIService
from app.modules.ai.schemas import ChatRequest
from app.modules.ai.models import TokenUsage
from sqlalchemy import select


@pytest.mark.asyncio
async def test_chat_records_usage_durably_and_syncs_the_discussed_farm(
    db_session, session_factory, monkeypatch
) -> None:
    monkeypatch.setattr("app.modules.ai.usage_ledger.SessionLocal", session_factory)
    service = AIService(SimpleNamespace(flush=AsyncMock()))
    service.profiles.get_by_user_id = AsyncMock(return_value=None)
    service.token_usage.count_today = AsyncMock(return_value=0)
    old_farm_id = uuid4()
    current_farm_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), title=None, farm_id=old_farm_id)
    service._get_or_create = AsyncMock(return_value=(conversation, []))
    service.messages.add = AsyncMock(
        side_effect=[SimpleNamespace(), SimpleNamespace(id="reply")]
    )
    service._load_farm = AsyncMock(return_value=SimpleNamespace(id=current_farm_id))
    service._safe_weather = AsyncMock(return_value=None)
    service.provider = SimpleNamespace(
        generate=AsyncMock(
            return_value=SimpleNamespace(
                model="gemini-test",
                input_tokens=10,
                output_tokens=20,
                latency_ms=30,
                provider="gemini",
                is_sample=False,
                text="reply",
                tokens=20,
            )
        )
    )
    monkeypatch.setattr("app.modules.ai.service.build_farm_memory", lambda *_args: "context")
    monkeypatch.setattr("app.modules.ai.service.build_system_instruction", lambda *_args: "system")
    monkeypatch.setattr("app.modules.ai.service.validate_response", lambda text, _language: text)

    user = SimpleNamespace(id=uuid4())
    result, _reply = await service.chat(
        user,
        ChatRequest(message="How is my crop?", farm_id=current_farm_id, language="en"),
    )

    assert result.farm_id == current_farm_id
    rows = (await db_session.execute(select(TokenUsage))).scalars().all()
    assert len(rows) == 1
    assert rows[0].module == "ai_chat"
    assert rows[0].farmer_id == user.id
