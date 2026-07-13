"""AI service — the AI router pipeline (docs/AI_DECISION_MATRIX.md, AI_PROMPTS.md).

    request → context/farm-memory → prompt → model → safety validation → persist

API → Service → Repository. Reuses the profile, farm and weather modules to build
farm memory; identity comes from the auth module. Gemini is the single provider.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import QuotaExceededError
from app.core.logging import get_logger
from app.modules.ai.constants import (
    DEFAULT_LANGUAGE,
    GEMINI_ROLE,
    HISTORY_WINDOW,
    TITLE_MAX_CHARS,
    Sender,
)
from app.modules.ai.context import build_farm_memory
from app.modules.ai.exceptions import ConversationNotFoundError
from app.modules.ai.models import AIConversation, AIMessage
from app.modules.ai.prompts import build_system_instruction
from app.modules.ai.provider import AIProvider, ChatTurn, get_default_provider
from app.modules.ai.repositories import (
    ConversationRepository,
    MessageRepository,
    TokenUsageRepository,
)
from app.modules.ai.schemas import ChatRequest
from app.modules.ai.validator import validate_response
from app.modules.auth.models import User
from app.modules.auth.repositories import FarmerProfileRepository
from app.modules.farms.models import Farm
from app.modules.farms.repositories import FarmRepository
from app.modules.weather.schemas import WeatherBundle
from app.modules.weather.service import WeatherService

logger = get_logger("ai.service")


def _derive_title(message: str) -> str:
    single = " ".join(message.strip().split())
    return single[:TITLE_MAX_CHARS] if single else "Chat"


def _day_start() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


class AIService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: AIProvider | None = None,
        weather_service: WeatherService | None = None,
    ) -> None:
        self.session = session
        self.conversations = ConversationRepository(session)
        self.messages = MessageRepository(session)
        self.token_usage = TokenUsageRepository(session)
        self.profiles = FarmerProfileRepository(session)
        self.farms = FarmRepository(session)
        self.provider = provider or get_default_provider()
        self.weather_service = weather_service

    # ----- Chat -----
    async def chat(
        self, user: User, req: ChatRequest
    ) -> tuple[AIConversation, AIMessage]:
        profile = await self.profiles.get_by_user_id(user.id)
        language = (
            req.language
            or (profile.language if profile else None)
            or DEFAULT_LANGUAGE
        )

        # Per-farmer daily quota — one script must not drain the shared Gemini budget.
        used = await self.token_usage.count_today(user.id, "ai_chat", since=_day_start())
        if used >= settings.ai_daily_chat_quota:
            raise QuotaExceededError()

        conversation, prior = await self._get_or_create(user, req, language)
        message = req.message.strip()

        await self.messages.add(
            AIMessage(
                conversation_id=conversation.id,
                sender=Sender.USER.value,
                message=message,
                language=language,
            )
        )

        farm = await self._load_farm(user, req.farm_id or conversation.farm_id)
        weather = await self._safe_weather(user, farm)
        system = build_system_instruction(language, build_farm_memory(profile, farm, weather))

        turns: list[ChatTurn] = [
            {"role": GEMINI_ROLE[m.sender], "content": m.message}
            for m in prior[-HISTORY_WINDOW:]
        ]
        result = await self.provider.generate(
            system=system, history=turns, message=message
        )
        await self.token_usage.record(
            farmer_id=user.id,
            module="ai_chat",
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
            provider=result.provider,
            is_sample=result.is_sample,
        )
        text = validate_response(result.text, language)

        reply = await self.messages.add(
            AIMessage(
                conversation_id=conversation.id,
                sender=Sender.ASSISTANT.value,
                message=text,
                language=language,
                model_used=result.model,
                token_count=result.tokens,
            )
        )

        if conversation.title is None:
            conversation.title = _derive_title(message)
        if farm is not None and conversation.farm_id is None:
            conversation.farm_id = farm.id
        await self.session.flush()
        logger.info("AI reply for conversation=%s user=%s", conversation.id, user.id)
        return conversation, reply

    async def _get_or_create(
        self, user: User, req: ChatRequest, language: str
    ) -> tuple[AIConversation, list[AIMessage]]:
        if req.conversation_id is not None:
            conversation = await self.conversations.get_for_user(
                req.conversation_id, user.id
            )
            if conversation is None:
                raise ConversationNotFoundError()
            return conversation, list(conversation.messages)

        conversation = AIConversation(
            user_id=user.id, farm_id=req.farm_id, language=language
        )
        self.session.add(conversation)
        await self.session.flush()
        return conversation, []

    async def _load_farm(
        self, user: User, farm_id: uuid.UUID | None
    ) -> Farm | None:
        if farm_id is None:
            return None
        return await self.farms.get_for_user(farm_id, user.id)

    async def _safe_weather(
        self, user: User, farm: Farm | None
    ) -> WeatherBundle | None:
        """Best-effort weather context; never fails the chat if unavailable."""
        if self.weather_service is None or farm is None:
            return None
        location = farm.location
        if location is None or location.latitude is None or location.longitude is None:
            return None
        try:
            return await self.weather_service.get_by_farm(user, farm.id)
        except Exception:
            logger.info("weather context unavailable; continuing without it")
            return None

    # ----- History -----
    async def list_conversations(
        self, user: User, *, page: int, page_size: int
    ) -> tuple[list[AIConversation], int]:
        offset = (page - 1) * page_size
        items = await self.conversations.list_for_user(
            user.id, limit=page_size, offset=offset
        )
        total = await self.conversations.count_for_user(user.id)
        return items, total

    async def get_conversation(
        self, user: User, conversation_id: uuid.UUID
    ) -> AIConversation:
        conversation = await self.conversations.get_for_user(conversation_id, user.id)
        if conversation is None:
            raise ConversationNotFoundError()
        return conversation

    async def delete_conversation(
        self, user: User, conversation_id: uuid.UUID
    ) -> None:
        conversation = await self.get_conversation(user, conversation_id)
        conversation.is_deleted = True
        conversation.deleted_at = datetime.now(UTC)
        await self.session.flush()
