"""AI-domain repositories (docs/BACKEND_ARCHITECTURE.md → Repository Pattern)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select

from app.modules.ai.constants import estimate_cost_inr
from app.modules.ai.models import AIConversation, AIMessage, TokenUsage
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


@dataclass(frozen=True)
class CostRow:
    """One aggregation bucket (by model, by module, or a time bucket)."""

    key: str
    requests: int
    input_tokens: int
    output_tokens: int
    cost_inr: float


class TokenUsageRepository(BaseRepository[TokenUsage]):
    """Persists per-request AI usage and aggregates it for the cost dashboard."""

    model = TokenUsage

    async def record(
        self,
        *,
        farmer_id: uuid.UUID | None,
        module: str,
        model: str,
        input_tokens: int | None,
        output_tokens: int | None,
        latency_ms: int | None,
        provider: str = "gemini",
        is_sample: bool = False,
    ) -> TokenUsage:
        """Record one AI call. Cost is derived from the shared INR cost table
        (0 when token counts are unknown — never fabricated)."""
        row = TokenUsage(
            farmer_id=farmer_id,
            module=module,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost_inr=estimate_cost_inr(model, input_tokens, output_tokens),
            is_sample=is_sample,
        )
        return await self.add(row)

    async def _grouped(self, column, *, since: datetime | None) -> list[CostRow]:
        stmt = select(
            column.label("bucket"),
            func.count().label("requests"),
            func.coalesce(func.sum(TokenUsage.input_tokens), 0).label("in_tok"),
            func.coalesce(func.sum(TokenUsage.output_tokens), 0).label("out_tok"),
            func.coalesce(func.sum(TokenUsage.estimated_cost_inr), 0.0).label("cost"),
        ).group_by(column)
        if since is not None:
            stmt = stmt.where(TokenUsage.created_at >= since)
        stmt = stmt.order_by(func.sum(TokenUsage.estimated_cost_inr).desc())
        result = await self.session.execute(stmt)
        return [
            CostRow(
                key=str(r.bucket),
                requests=int(r.requests),
                input_tokens=int(r.in_tok),
                output_tokens=int(r.out_tok),
                cost_inr=round(float(r.cost), 6),
            )
            for r in result
        ]

    async def by_model(self, *, since: datetime | None = None) -> list[CostRow]:
        return await self._grouped(TokenUsage.model, since=since)

    async def by_module(self, *, since: datetime | None = None) -> list[CostRow]:
        return await self._grouped(TokenUsage.module, since=since)

    async def daily(self, *, since: datetime | None = None) -> list[CostRow]:
        """Per-day totals (cross-db: groups on the date part of created_at)."""
        return await self._grouped(func.date(TokenUsage.created_at), since=since)
