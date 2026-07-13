"""AI Chat API routes (docs/API_CONTRACT.md → AI CHAT).

    POST   /ai/chat
    GET    /ai/history            GET /ai/history/{id}    DELETE /ai/history/{id}

Every route is authenticated and thin — the AI router pipeline lives in
``AIService``. (Voice and image chat are deferred to their own modules.)
"""
from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Query

from app.modules.ai.dependencies import AIServiceDep, CurrentUser
from app.modules.ai.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetailOut,
    ConversationOut,
    MessageOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=SuccessResponse[ChatResponse])
async def chat(
    payload: ChatRequest, current_user: CurrentUser, service: AIServiceDep
):
    """Send a message to the AI assistant and get a reply."""
    conversation, reply = await service.chat(current_user, payload)
    data = ChatResponse(
        conversation_id=conversation.id,
        title=conversation.title,
        reply=MessageOut.model_validate(reply),
    )
    return success(data, message="Reply generated")


@router.get(
    "/history", response_model=SuccessResponse[PaginatedData[ConversationOut]]
)
async def list_history(
    current_user: CurrentUser,
    service: AIServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List the farmer's past conversations (most recent first)."""
    items, total = await service.list_conversations(
        current_user, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[ConversationOut.from_conversation(c) for c in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )
    return success(data)


@router.get(
    "/history/{conversation_id}",
    response_model=SuccessResponse[ConversationDetailOut],
)
async def get_history(
    conversation_id: uuid.UUID, current_user: CurrentUser, service: AIServiceDep
):
    """Fetch a single conversation with its full message thread."""
    conversation = await service.get_conversation(current_user, conversation_id)
    return success(ConversationDetailOut.from_conversation(conversation))


@router.delete(
    "/history/{conversation_id}", response_model=SuccessResponse[None]
)
async def delete_history(
    conversation_id: uuid.UUID, current_user: CurrentUser, service: AIServiceDep
):
    """Delete a conversation (soft delete)."""
    await service.delete_conversation(current_user, conversation_id)
    return success(None, message="Conversation deleted")
