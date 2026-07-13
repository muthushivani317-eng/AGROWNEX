"""Expert Connect constants (docs: this is a *future-ready* consultation platform).

A structured question-and-answer system connecting farmers with verified
agricultural experts (TNAU / KVK / Government / private). Deliberately not a public
chat room: every consultation is a tracked, immutable-history Q&A thread. The
enums below are the stable vocabulary shared by the engine, providers and API so
future channels (WhatsApp / live chat / video / email) and AI-assisted replies can
be added without redesign.
"""
from __future__ import annotations

import os
from enum import StrEnum

DEFAULT_LANGUAGE = "ta"

# Pagination (docs/CLAUDE.md → every API must include pagination).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Provider selection — absent means the in-app mock desk network (no external channel).
EXPERT_PROVIDER = os.getenv("EXPERT_PROVIDER", "")


class ExpertType(StrEnum):
    """Where a verified expert comes from. Only institutional desks in V1 — never
    fabricated individuals (docs/PRODUCT_RULES.md)."""

    TNAU = "tnau"
    KVK = "kvk"
    GOVT_OFFICER = "govt_officer"
    KISAN_CALL_CENTRE = "kisan_call_centre"
    AGRONOMIST = "agronomist"  # future: private consultants
    PRIVATE = "private"


class ConsultationCategory(StrEnum):
    """The issue area a farmer is asking about (drives expert assignment)."""

    CROP_DISEASE = "crop_disease"
    PEST_CONTROL = "pest_control"
    SOIL_HEALTH = "soil_health"
    IRRIGATION = "irrigation"
    FERTILIZER = "fertilizer"
    WEATHER = "weather"
    MARKET = "market"
    SCHEME = "scheme"
    SEED = "seed"
    ORGANIC = "organic"
    GENERAL = "general"


class ConsultationPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ConsultationStatus(StrEnum):
    """Consultation lifecycle. Terminal = resolved / closed / cancelled."""

    SUBMITTED = "submitted"          # created, not yet assigned
    ASSIGNED = "assigned"            # routed to a verified expert desk
    IN_PROGRESS = "in_progress"      # expert is working on it
    AWAITING_FARMER = "awaiting_farmer"   # expert asked for more info
    AWAITING_EXPERT = "awaiting_expert"   # farmer replied, expert to respond
    RESOLVED = "resolved"            # answered / closed by resolution
    CLOSED = "closed"                # archived
    CANCELLED = "cancelled"          # withdrawn by the farmer


# Statuses a farmer may set directly (the rest are expert/system driven).
FARMER_SETTABLE_STATUSES: frozenset[str] = frozenset(
    {ConsultationStatus.RESOLVED.value, ConsultationStatus.CANCELLED.value}
)

# Terminal statuses — no further transitions allowed.
TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        ConsultationStatus.RESOLVED.value,
        ConsultationStatus.CLOSED.value,
        ConsultationStatus.CANCELLED.value,
    }
)

# A farmer reply while awaiting them moves the thread back to the expert.
FARMER_REPLY_STATUS_MAP: dict[str, str] = {
    ConsultationStatus.AWAITING_FARMER.value: ConsultationStatus.AWAITING_EXPERT.value,
    ConsultationStatus.ASSIGNED.value: ConsultationStatus.AWAITING_EXPERT.value,
}


class SenderType(StrEnum):
    FARMER = "farmer"
    EXPERT = "expert"
    SYSTEM = "system"


class AttachmentKind(StrEnum):
    IMAGE = "image"
    VOICE = "voice"      # reserved for future (voice notes)
    DOCUMENT = "document"


class ConsultationChannel(StrEnum):
    """Where the consultation is handled. Only IN_APP is active in V1."""

    IN_APP = "in_app"
    WHATSAPP = "whatsapp"
    LIVE_CHAT = "live_chat"
    VIDEO = "video"
    EMAIL = "email"


# --------------------------------------------------------------------------- #
# Deterministic assignment weights (transparent, tunable — see engine.py).
# --------------------------------------------------------------------------- #
SCORE_CATEGORY_MATCH = 40
SCORE_CROP_MATCH = 20
SCORE_DISTRICT_MATCH = 20
SCORE_LANGUAGE_MATCH = 10
SCORE_VERIFIED = 10
SCORE_AVAILABLE = 5
SCORE_GENERALIST = 8   # a general-purpose desk is a safe fallback
# Each currently-open consultation already assigned to an expert lowers the score
# so load is spread across desks (deterministic tie-break stays by expert id).
SCORE_LOAD_PENALTY = 3
