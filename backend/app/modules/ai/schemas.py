"""AI Chat request/response schemas (docs/API_CONTRACT.md → AI CHAT)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.ai.constants import MAX_MESSAGE_CHARS
from app.modules.ai.models import AIConversation


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    conversation_id: uuid.UUID | None = None
    farm_id: uuid.UUID | None = None
    language: str | None = Field(default=None, pattern="^(ta|en)$")


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender: str
    message: str
    language: str
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    title: str | None
    reply: MessageOut


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str | None
    language: str
    last_message: str | None
    message_count: int
    started_at: datetime
    updated_at: datetime

    @classmethod
    def from_conversation(cls, conv: AIConversation) -> ConversationOut:
        messages = conv.messages
        return cls(
            id=conv.id,
            title=conv.title,
            language=conv.language,
            last_message=messages[-1].message if messages else None,
            message_count=len(messages),
            started_at=conv.started_at,
            updated_at=conv.updated_at,
        )


class ConversationDetailOut(BaseModel):
    id: uuid.UUID
    title: str | None
    language: str
    started_at: datetime
    messages: list[MessageOut]

    @classmethod
    def from_conversation(cls, conv: AIConversation) -> ConversationDetailOut:
        return cls(
            id=conv.id,
            title=conv.title,
            language=conv.language,
            started_at=conv.started_at,
            messages=[MessageOut.model_validate(m) for m in conv.messages],
        )
