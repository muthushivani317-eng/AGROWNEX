"""AI-specific exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import AppError, NotFoundError


class ConversationNotFoundError(NotFoundError):
    error_code = "conversation_not_found"
    message = "Conversation not found."


class AIUnavailableError(AppError):
    status_code = 503
    error_code = "ai_unavailable"
    # Honest, Tamil-first degradation when Gemini is down (never a fabricated answer).
    message = (
        "AI உதவியாளர் தற்காலிகமாக கிடைக்கவில்லை. சிறிது நேரம் கழித்து முயற்சிக்கவும். "
        "/ The AI assistant is temporarily unavailable. Please try again."
    )
