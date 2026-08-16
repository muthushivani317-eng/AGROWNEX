"""Expert providers (docs: provider abstraction; future channels without redesign).

``ExpertProvider`` is the seam that supplies the verified expert network and routes
a submitted consultation to it — without the service, API or frontend knowing
*which* network. V1 ships a ``MockExpertProvider`` that:

* seeds **real, institutional** agricultural advisory desks (TNAU, KVK, the Kisan
  Call Centre, State Agriculture Officers) — never fabricated individuals
  (docs/PRODUCT_RULES.md), and
* **acknowledges** an assigned consultation with a *system* message (receipt only —
  it never fabricates an expert's agronomic opinion).

Future providers (WhatsApp, live chat, video, email, government-officer or private
consultant networks, AI-assisted replies) implement the same Protocol and are
selected in ``get_default_provider`` with no change to the rest of the module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.core.logging import get_logger
from app.core.provider_policy import test_mocks_enabled
from app.modules.experts.constants import (
    EXPERT_PROVIDER,
    ConsultationCategory,
    ConsultationChannel,
    ExpertType,
)

logger = get_logger("experts.provider")

_C = ConsultationCategory


@dataclass(frozen=True)
class SeedExpert:
    """A verified expert desk supplied by a provider (source-agnostic)."""

    slug: str
    full_name: str
    expert_type: str
    organization: str
    title: str
    bio: str
    categories: tuple[str, ...]
    crops: tuple[str, ...] = ()
    districts: tuple[str, ...] = ()
    languages: tuple[str, ...] = ("ta", "en")
    is_generalist: bool = False
    source: str | None = None
    contact: str | None = None


@dataclass(frozen=True)
class AssignmentRef:
    """The minimal view of a consultation handed to a provider for routing."""

    consultation_id: str
    category: str
    crop: str | None
    subject: str
    expert_name: str | None


@dataclass(frozen=True)
class AcknowledgementResult:
    """A provider's receipt for an assigned consultation (a *system* message)."""

    channel: str
    message: str
    reference: str | None = None


@dataclass(frozen=True)
class ExpertReply:
    """Future-ready: a real expert/AI reply from a channel (empty in V1)."""

    body: str
    language: str = "ta"
    reference: str | None = None
    fields: dict = field(default_factory=dict)


class ExpertProvider(Protocol):
    """Supplies the verified expert network and routes consultations to it."""

    name: str

    async def fetch_experts(self) -> list[SeedExpert]: ...

    async def acknowledge(self, ref: AssignmentRef) -> AcknowledgementResult: ...

    async def poll_replies(self, ref: AssignmentRef) -> list[ExpertReply]: ...


# --------------------------------------------------------------------------- #
# The seeded verified desks (real institutions; no fabricated individuals).
# --------------------------------------------------------------------------- #
_SEED_EXPERTS: tuple[SeedExpert, ...] = (
    SeedExpert(
        slug="tnau-agritech-helpline",
        full_name="TNAU Agri-Tech Advisory",
        expert_type=ExpertType.TNAU.value,
        organization="Tamil Nadu Agricultural University",
        title="University Advisory Desk",
        bio=(
            "Advisory desk of Tamil Nadu Agricultural University covering crop "
            "management, pest and disease guidance and good agricultural practices."
        ),
        categories=(
            _C.GENERAL.value, _C.CROP_DISEASE.value, _C.PEST_CONTROL.value,
            _C.FERTILIZER.value, _C.SEED.value, _C.ORGANIC.value,
        ),
        languages=("ta", "en"),
        is_generalist=True,
        source="https://tnau.ac.in",
    ),
    SeedExpert(
        slug="tnau-plant-clinic",
        full_name="TNAU Plant Health Clinic",
        expert_type=ExpertType.TNAU.value,
        organization="Tamil Nadu Agricultural University",
        title="Plant Health Specialist Desk",
        bio="Diagnoses crop diseases and pest problems from farmer photos and notes.",
        categories=(_C.CROP_DISEASE.value, _C.PEST_CONTROL.value),
        languages=("ta", "en"),
        source="https://tnau.ac.in",
    ),
    SeedExpert(
        slug="kvk-farm-advisory",
        full_name="Krishi Vigyan Kendra Farm Advisory",
        expert_type=ExpertType.KVK.value,
        organization="Krishi Vigyan Kendra (ICAR)",
        title="District Farm Science Centre",
        bio=(
            "District-level Krishi Vigyan Kendra advisory for soil health, "
            "irrigation, seeds and location-specific crop guidance."
        ),
        categories=(
            _C.SOIL_HEALTH.value, _C.IRRIGATION.value, _C.SEED.value,
            _C.FERTILIZER.value, _C.GENERAL.value,
        ),
        languages=("ta", "en"),
        is_generalist=True,
        source="https://kvk.icar.gov.in",
    ),
    SeedExpert(
        slug="kisan-call-centre",
        full_name="Kisan Call Centre",
        expert_type=ExpertType.KISAN_CALL_CENTRE.value,
        organization="Ministry of Agriculture & Farmers Welfare",
        title="National Farmer Helpline",
        bio="National toll-free farmer helpline for all agricultural queries.",
        categories=(_C.GENERAL.value, _C.SCHEME.value, _C.MARKET.value, _C.WEATHER.value),
        languages=("ta", "en", "hi"),
        is_generalist=True,
        source="https://mkisan.gov.in",
        contact="1800-180-1551",
    ),
    SeedExpert(
        slug="state-agriculture-officer",
        full_name="State Agriculture Officer Desk",
        expert_type=ExpertType.GOVT_OFFICER.value,
        organization="Tamil Nadu Department of Agriculture",
        title="Block Agriculture Officer",
        bio=(
            "State agriculture department desk for schemes, subsidies, input "
            "supply and field-level guidance."
        ),
        categories=(_C.SCHEME.value, _C.FERTILIZER.value, _C.SEED.value, _C.GENERAL.value),
        languages=("ta", "en"),
        is_generalist=True,
        source="https://www.tn.gov.in/department/1",
    ),
)


class MockExpertProvider:
    """In-app desk network: seeds verified desks and acknowledges consultations.

    It never fabricates an expert's agronomic opinion — ``poll_replies`` returns
    nothing until a real expert/AI channel is wired in.
    """

    name = "mock"

    async def fetch_experts(self) -> list[SeedExpert]:
        return list(_SEED_EXPERTS)

    async def acknowledge(self, ref: AssignmentRef) -> AcknowledgementResult:
        desk = ref.expert_name or "a verified expert desk"
        logger.info(
            "consultation %s routed to %s (mock, in-app)", ref.consultation_id, desk
        )
        return AcknowledgementResult(
            channel=ConsultationChannel.IN_APP.value,
            message=(
                f"Your question has been received by {desk}. "
                "A verified expert will review it and reply here."
            ),
            reference=None,
        )

    async def poll_replies(self, ref: AssignmentRef) -> list[ExpertReply]:
        # No fabricated expert opinions in V1 — real replies arrive via a real
        # channel (future) or an expert-facing interface.
        return []


class UnavailableExpertProvider:
    """Provides no desk or acknowledgement when no real network is connected."""

    name = "unavailable"

    async def fetch_experts(self) -> list[SeedExpert]:
        return []

    async def acknowledge(self, ref: AssignmentRef) -> AcknowledgementResult:
        raise RuntimeError("Expert network is not configured")

    async def poll_replies(self, ref: AssignmentRef) -> list[ExpertReply]:
        return []


def get_default_provider() -> ExpertProvider:
    """Select the configured provider (mock desk network until one is wired in)."""
    if test_mocks_enabled():
        logger.info("expert provider: explicit development/test mock")
        return MockExpertProvider()
    if EXPERT_PROVIDER:
        logger.warning("expert provider '%s' is not wired", EXPERT_PROVIDER)
    else:
        logger.warning("expert provider unavailable: no real network configured")
    return UnavailableExpertProvider()
