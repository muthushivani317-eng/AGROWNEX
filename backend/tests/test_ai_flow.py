"""Integration tests for the AI service (fake Gemini provider, no network)."""
from __future__ import annotations

import uuid

import pytest
from app.modules.ai.exceptions import ConversationNotFoundError
from app.modules.ai.provider import AIResult
from app.modules.ai.schemas import ChatRequest
from app.modules.ai.service import AIService
from app.modules.auth.models import User
from app.modules.auth.profile_models import FarmerProfile
from app.modules.farms.models import Farm


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate(self, *, system: str, history: list, message: str) -> AIResult:
        self.calls.append({"system": system, "history": history, "message": message})
        return AIResult(text=f"Echo: {message}", model="fake-model", tokens=42)


async def _make_user(db_session, uid: str = "fb-ai-1") -> User:
    user = User(
        firebase_uid=uid,
        phone_number="+919876522222",
        email=None,
        is_phone_verified=True,
        is_email_verified=False,
        status="active",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_chat_creates_conversation_and_persists_turns(db_session):
    service = AIService(db_session, provider=FakeProvider())
    user = await _make_user(db_session)

    conversation, reply = await service.chat(
        user, ChatRequest(message="How do I grow paddy?")
    )
    assert reply.sender == "assistant"
    assert reply.message == "Echo: How do I grow paddy?"
    assert reply.model_used == "fake-model"
    assert conversation.title == "How do I grow paddy?"

    detail = await service.get_conversation(user, conversation.id)
    assert [m.sender for m in detail.messages] == ["user", "assistant"]


async def test_chat_continues_existing_conversation_with_history(db_session):
    provider = FakeProvider()
    service = AIService(db_session, provider=provider)
    user = await _make_user(db_session)

    conversation, _ = await service.chat(user, ChatRequest(message="First question"))
    await service.chat(
        user,
        ChatRequest(message="Follow up", conversation_id=conversation.id),
    )

    # The second call receives the prior user + assistant turns as history.
    second_history = provider.calls[1]["history"]
    assert [turn["role"] for turn in second_history] == ["user", "model"]
    assert second_history[0]["content"] == "First question"


async def test_chat_includes_farm_memory(db_session):
    provider = FakeProvider()
    service = AIService(db_session, provider=provider)
    user = await _make_user(db_session)
    db_session.add(
        FarmerProfile(
            user_id=user.id, full_name="Selvi", district="madurai", language="ta"
        )
    )
    farm = Farm(user_id=user.id, name="Riverside", crop="paddy", crop_variety="ADT 43")
    db_session.add(farm)
    await db_session.flush()

    await service.chat(
        user, ChatRequest(message="advice?", farm_id=farm.id)
    )
    system = provider.calls[0]["system"]
    assert "Riverside" in system
    assert "madurai" in system
    # PII minimization (2026-08 pre-release audit): the farmer's name never
    # reaches the Gemini prompt — see build_farm_memory() in ai/context.py.
    assert "Selvi" not in system


async def test_language_defaults_to_profile(db_session):
    service = AIService(db_session, provider=FakeProvider())
    user = await _make_user(db_session)
    db_session.add(
        FarmerProfile(user_id=user.id, full_name="Raj", language="en")
    )
    await db_session.flush()

    _, reply = await service.chat(user, ChatRequest(message="hello"))
    assert reply.language == "en"


async def test_explicit_language_overrides(db_session):
    provider = FakeProvider()
    service = AIService(db_session, provider=provider)
    user = await _make_user(db_session)
    _, reply = await service.chat(
        user, ChatRequest(message="hi", language="ta")
    )
    assert reply.language == "ta"
    assert "Tamil" in provider.calls[0]["system"]


async def test_history_list_and_delete(db_session):
    service = AIService(db_session, provider=FakeProvider())
    user = await _make_user(db_session)
    c1, _ = await service.chat(user, ChatRequest(message="one"))
    c2, _ = await service.chat(user, ChatRequest(message="two"))

    items, total = await service.list_conversations(user, page=1, page_size=20)
    assert total == 2
    assert {c.id for c in items} == {c1.id, c2.id}

    await service.delete_conversation(user, c1.id)
    _, total_after = await service.list_conversations(user, page=1, page_size=20)
    assert total_after == 1
    with pytest.raises(ConversationNotFoundError):
        await service.get_conversation(user, c1.id)


async def test_unknown_conversation_raises(db_session):
    service = AIService(db_session, provider=FakeProvider())
    user = await _make_user(db_session)
    with pytest.raises(ConversationNotFoundError):
        await service.chat(
            user, ChatRequest(message="hi", conversation_id=uuid.uuid4())
        )


async def test_ownership_isolation(db_session):
    service = AIService(db_session, provider=FakeProvider())
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    conversation, _ = await service.chat(owner, ChatRequest(message="private"))

    with pytest.raises(ConversationNotFoundError):
        await service.get_conversation(other, conversation.id)


class UnsafeAdviceProvider:
    """Simulates Gemini drifting from its own system prompt (2026-08
    pre-release audit): the reply text itself is what the output safety
    check in validator.py needs to catch, not a provider-level failure."""

    async def generate(self, *, system: str, history: list, message: str) -> AIResult:
        return AIResult(
            text="Don't worry, this will guarantee your yield doubles this season.",
            model="fake-model",
            tokens=42,
        )


async def test_unsafe_advice_is_replaced_with_the_safe_fallback(db_session):
    service = AIService(db_session, provider=UnsafeAdviceProvider())
    user = await _make_user(db_session)

    _, reply = await service.chat(
        user, ChatRequest(message="Will I get a good harvest?", language="en")
    )

    assert "guarantee" not in reply.message.lower()
    assert "agriculture officer" in reply.message
