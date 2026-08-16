"""Produce background jobs (pattern: app.modules.market.jobs).

Pure orchestration over the existing repository so it is unit-testable with a
fixture session (no network). Wired into the ARQ worker on a schedule.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.timezone import today_ist
from app.modules.produce.constants import ProduceStatus
from app.modules.produce.models import OfferStatusHistory
from app.modules.produce.repository import ProduceRepository

logger = get_logger("produce.jobs")

# Grace period after the farmer's own stated harvest date before an
# un-acted-on offer (draft/submitted/planned) is moved to EXPIRED. Gives the
# farmer a reasonable window to mark it harvested/withdrawn themselves before
# the system does it for them.
EXPIRY_GRACE_DAYS = 14


async def expire_stale_offers(session: AsyncSession) -> dict[str, int]:
    """Move offers whose harvest date is long past with no farmer action to EXPIRED.

    ProduceStatus.EXPIRED was defined (docs: produce constants) but nothing ever
    set it -- stale offers just sat in draft/submitted/planned indefinitely
    instead of moving into the concluded/history lifecycle (found in the 2026-08
    pre-release audit). This never guesses at market outcomes: it only records
    that the farmer's own stated harvest window passed without them updating
    the offer, which is a fact the app already has, not a fabricated one.
    """
    repo = ProduceRepository(session)
    cutoff = today_ist() - timedelta(days=EXPIRY_GRACE_DAYS)
    offers = await repo.list_stale_open_offers(cutoff=cutoff)
    for offer in offers:
        old_status = offer.status
        offer.status = ProduceStatus.EXPIRED.value
        await repo.add_status_history(
            OfferStatusHistory(
                offer_id=offer.id,
                old_status=old_status,
                new_status=ProduceStatus.EXPIRED.value,
                changed_by=None,
                note=(
                    "Automatically expired: expected harvest date passed "
                    f"more than {EXPIRY_GRACE_DAYS} days ago with no update."
                ),
            )
        )
    logger.info("produce expiry: %s offers moved to expired", len(offers))
    return {"expired": len(offers)}
