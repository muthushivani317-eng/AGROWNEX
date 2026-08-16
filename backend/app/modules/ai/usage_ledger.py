from __future__ import annotations

import uuid

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.modules.ai.repositories import TokenUsageRepository

logger = get_logger("ai.usage_ledger")


async def record_usage_durable(
    *,
    farmer_id: uuid.UUID | None,
    module: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    latency_ms: int | None,
    provider: str = "gemini",
    is_sample: bool = False,
) -> None:
    """Record one AI usage row in its own transaction.

    The row survives later failures in the caller's request, such as a valid
    provider response concluding that no plant was detected. A ledger write
    failure is logged rather than breaking the farmer's request.
    """
    try:
        async with SessionLocal() as usage_session:
            await TokenUsageRepository(usage_session).record(
                farmer_id=farmer_id,
                module=module,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                provider=provider,
                is_sample=is_sample,
            )
            await usage_session.commit()
    except Exception:
        logger.exception(
            "failed to durably record AI usage (module=%s farmer=%s)",
            module,
            farmer_id,
        )
