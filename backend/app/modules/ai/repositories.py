"""AI-domain repositories (docs/BACKEND_ARCHITECTURE.md → Repository Pattern)."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.modules.ai.models import AIConversation, AIMessage
from app.shared.base_repository import BaseRepository


class ConversationRepository(BaseRepository[AIConversation]):
    model = AIConversation

    async def get_for_user(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> AIConversation | None:
        result = await self.session.execute(
            select(AIConversation).where(
                AIConversation.id == conversation_id,
                AIConversation.user_id == user_id,
                AIConversation.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int, offset: int
    ) -> list[AIConversation]:
        result = await self.session.execute(
            select(AIConversation)
            .where(
                AIConversation.user_id == user_id,
                AIConversation.is_deleted.is_(False),
            )
            .order_by(AIConversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().unique().all())

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(AIConversation)
            .where(
                AIConversation.user_id == user_id,
                AIConversation.is_deleted.is_(False),
            )
        )
        return int(result.scalar_one())


class MessageRepository(BaseRepository[AIMessage]):
    model = AIMessage
