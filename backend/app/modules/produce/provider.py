"""Produce providers (docs: provider abstraction).

``ProduceProvider`` is the seam that lets a submitted harvest offer be routed to a
procurement channel without the service, API or frontend knowing *which* channel.
V1 ships a ``MockProduceProvider`` that acknowledges submissions (so the flow is
end-to-end) and returns **no** buyer interest — buyers are never fabricated
(docs/PRODUCT_RULES.md). Future providers (eNAM, FPO procurement, private buyers,
export companies, an admin portal) implement the same Protocol and are selected in
``get_default_provider`` with no change to the rest of the module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from app.core.logging import get_logger
from app.core.provider_policy import test_mocks_enabled
from app.modules.produce.constants import ProcurementChannel

logger = get_logger("produce.provider")


@dataclass(frozen=True)
class OfferRef:
    """The minimal, source-agnostic view of an offer handed to a provider."""

    id: str
    crop_name: str
    quantity: float
    unit: str
    district: str | None = None


@dataclass(frozen=True)
class ProcurementAck:
    """A provider's acknowledgement that an offer was received for planning."""

    channel: str
    reference: str
    status: str = "received"
    message: str | None = None


@dataclass(frozen=True)
class BuyerInterestRecord:
    """Future-ready: a buyer's interest from a channel (empty in V1)."""

    channel: str
    buyer_name: str | None = None
    buyer_type: str | None = None
    contact: str | None = None
    offered_price: float | None = None
    quantity: float | None = None
    external_reference: str | None = None


class ProduceProvider(Protocol):
    """Routes verified harvest offers to a procurement channel. The external seam."""

    channel: str

    async def submit(self, offer: OfferRef) -> ProcurementAck | None: ...

    async def buyer_interest(self, offer: OfferRef) -> list[BuyerInterestRecord]: ...


class MockProduceProvider:
    """Deterministic local channel: acknowledges offers, fabricates no buyers."""

    channel = ProcurementChannel.MOCK.value

    def __init__(self, *, reference_factory=None) -> None:
        self._reference_factory = reference_factory or (lambda: uuid4().hex[:12])

    async def submit(self, offer: OfferRef) -> ProcurementAck:
        reference = f"MOCK-{self._reference_factory()}".upper()
        logger.info("produce offer %s acknowledged (mock) → %s", offer.id, reference)
        return ProcurementAck(
            channel=self.channel,
            reference=reference,
            status="received",
            message="Recorded for procurement planning.",
        )

    async def buyer_interest(self, offer: OfferRef) -> list[BuyerInterestRecord]:
        # No verified buyers in V1 — never fabricate.
        return []


class UnavailableProduceProvider:
    """Keeps local listings usable without claiming external procurement."""

    channel = "not_connected"

    async def submit(self, offer: OfferRef) -> ProcurementAck | None:
        return None

    async def buyer_interest(self, offer: OfferRef) -> list[BuyerInterestRecord]:
        return []


def get_default_provider() -> ProduceProvider:
    """Select the configured provider (mock until a real channel is wired in)."""
    if test_mocks_enabled():
        logger.info("produce provider: explicit development/test mock")
        return MockProduceProvider()
    logger.warning("produce provider unavailable: no external procurement channel")
    return UnavailableProduceProvider()
