"""Organic Inputs Marketplace constants — dynamic catalogue, supplier onboarding
and production-batch state machines (docs: AGROWAI_ORGANIC_INPUTS_MARKETPLACE).

FOUNDATION PHASE ONLY. Every status a batch/supplier can eventually reach is
enumerated below so later phases (inspection, testing, procurement, inventory,
buying) don't need another migration just to add a status value -- but only the
edges in *_ADMIN_DECISIONS are reachable through an endpoint today. A batch can
reach INSPECTION_REQUIRED and then sits there until the QC phase adds the
inspection/testing endpoints that move it further; nothing in this phase can
skip straight to APPROVED/RELEASED_FOR_SALE.
"""

from __future__ import annotations

from enum import StrEnum


class CatalogStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class NewProductRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SupplierStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    CLARIFICATION_REQUIRED = "clarification_required"
    INSPECTION_SCHEDULED = "inspection_scheduled"
    INSPECTION_COMPLETED = "inspection_completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


# Full target lifecycle (docs: section 4). Kept for reference/validation of any
# status value ever stored; SUPPLIER_ADMIN_DECISIONS below is the narrower set
# actually reachable through an endpoint in this phase.
SUPPLIER_TRANSITIONS: dict[SupplierStatus, set[SupplierStatus]] = {
    SupplierStatus.DRAFT: {SupplierStatus.SUBMITTED},
    SupplierStatus.SUBMITTED: {SupplierStatus.UNDER_REVIEW},
    SupplierStatus.UNDER_REVIEW: {
        SupplierStatus.CLARIFICATION_REQUIRED,
        SupplierStatus.INSPECTION_SCHEDULED,
        SupplierStatus.REJECTED,
    },
    SupplierStatus.CLARIFICATION_REQUIRED: {SupplierStatus.UNDER_REVIEW},
    SupplierStatus.INSPECTION_SCHEDULED: {SupplierStatus.INSPECTION_COMPLETED},
    SupplierStatus.INSPECTION_COMPLETED: {SupplierStatus.APPROVED, SupplierStatus.REJECTED},
    SupplierStatus.APPROVED: {SupplierStatus.SUSPENDED, SupplierStatus.EXPIRED},
    SupplierStatus.SUSPENDED: {SupplierStatus.APPROVED, SupplierStatus.EXPIRED},
    SupplierStatus.REJECTED: set(),
    SupplierStatus.EXPIRED: set(),
}

# Reachable today via POST /admin/organic-inputs/suppliers/{id}/decision.
SUPPLIER_ADMIN_DECISIONS: dict[SupplierStatus, set[SupplierStatus]] = {
    SupplierStatus.SUBMITTED: {SupplierStatus.UNDER_REVIEW},
    SupplierStatus.UNDER_REVIEW: {
        SupplierStatus.CLARIFICATION_REQUIRED,
        SupplierStatus.INSPECTION_SCHEDULED,
        SupplierStatus.REJECTED,
    },
    SupplierStatus.CLARIFICATION_REQUIRED: {SupplierStatus.UNDER_REVIEW},
    SupplierStatus.INSPECTION_SCHEDULED: {SupplierStatus.INSPECTION_COMPLETED},
    SupplierStatus.INSPECTION_COMPLETED: {SupplierStatus.APPROVED, SupplierStatus.REJECTED},
    SupplierStatus.APPROVED: {SupplierStatus.SUSPENDED, SupplierStatus.EXPIRED},
    SupplierStatus.SUSPENDED: {SupplierStatus.APPROVED, SupplierStatus.EXPIRED},
}

# A batch may only be created/submitted by a supplier in this status.
SUPPLIER_STATUS_MAY_SUBMIT_BATCH = SupplierStatus.APPROVED


class BatchStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    CLARIFICATION_REQUIRED = "clarification_required"
    INSPECTION_REQUIRED = "inspection_required"
    INSPECTION_COMPLETED = "inspection_completed"
    SAMPLE_COLLECTED = "sample_collected"
    TESTING = "testing"
    RETEST_REQUIRED = "retest_required"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    REJECTED = "rejected"
    PROCUREMENT_OFFERED = "procurement_offered"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    RECEIVED = "received"
    QUARANTINED = "quarantined"
    RELEASED_FOR_SALE = "released_for_sale"
    SOLD_OUT = "sold_out"
    EXPIRED = "expired"
    RECALLED = "recalled"


# Full target lifecycle (docs: section 5). Everything past INSPECTION_REQUIRED
# is inert enum surface for the QC/procurement/inventory phases to activate --
# not itself a security boundary. BATCH_ADMIN_DECISIONS below is what's actually
# enforced by the router today.
BATCH_TRANSITIONS: dict[BatchStatus, set[BatchStatus]] = {
    BatchStatus.DRAFT: {BatchStatus.SUBMITTED},
    BatchStatus.SUBMITTED: {BatchStatus.UNDER_REVIEW},
    BatchStatus.UNDER_REVIEW: {
        BatchStatus.CLARIFICATION_REQUIRED,
        BatchStatus.INSPECTION_REQUIRED,
        BatchStatus.REJECTED,
    },
    BatchStatus.CLARIFICATION_REQUIRED: {BatchStatus.UNDER_REVIEW},
    BatchStatus.INSPECTION_REQUIRED: {BatchStatus.INSPECTION_COMPLETED},
    BatchStatus.INSPECTION_COMPLETED: {BatchStatus.SAMPLE_COLLECTED, BatchStatus.REJECTED},
    BatchStatus.SAMPLE_COLLECTED: {BatchStatus.TESTING},
    BatchStatus.TESTING: {
        BatchStatus.RETEST_REQUIRED,
        BatchStatus.APPROVED,
        BatchStatus.PARTIALLY_APPROVED,
        BatchStatus.REJECTED,
    },
    BatchStatus.RETEST_REQUIRED: {BatchStatus.SAMPLE_COLLECTED},
    BatchStatus.APPROVED: {BatchStatus.PROCUREMENT_OFFERED},
    BatchStatus.PARTIALLY_APPROVED: {BatchStatus.PROCUREMENT_OFFERED},
    BatchStatus.PROCUREMENT_OFFERED: {BatchStatus.OFFER_ACCEPTED, BatchStatus.OFFER_REJECTED},
    BatchStatus.OFFER_ACCEPTED: {BatchStatus.RECEIVED},
    BatchStatus.OFFER_REJECTED: set(),
    BatchStatus.RECEIVED: {BatchStatus.QUARANTINED, BatchStatus.RELEASED_FOR_SALE},
    BatchStatus.QUARANTINED: {BatchStatus.RELEASED_FOR_SALE, BatchStatus.REJECTED},
    BatchStatus.RELEASED_FOR_SALE: {
        BatchStatus.SOLD_OUT,
        BatchStatus.EXPIRED,
        BatchStatus.RECALLED,
    },
    BatchStatus.SOLD_OUT: set(),
    BatchStatus.REJECTED: set(),
    BatchStatus.EXPIRED: set(),
    BatchStatus.RECALLED: set(),
}

# Reachable today via POST /admin/organic-inputs/batches/{id}/decision.
# INSPECTION_REQUIRED -> INSPECTION_COMPLETED/REJECTED is deliberately NOT
# here -- it's only reachable via the dedicated
# POST .../batches/{id}/inspection endpoint, which requires a real
# BatchInspection record. Likewise INSPECTION_COMPLETED -> SAMPLE_COLLECTED
# only via POST .../samples (a real BatchSample), and SAMPLE_COLLECTED ->
# TESTING only via POST .../samples/{sample_id}/test-results (a real
# BatchTestResult). This dict is for the *outcome* decision only, once QC has
# entered at least one test result -- see decide_batch's test-result guard.
#
# Procurement phase: APPROVED/PARTIALLY_APPROVED -> PROCUREMENT_OFFERED needs
# a real BatchProcurementOffer (POST .../procurement-offer); PROCUREMENT_OFFERED
# -> OFFER_ACCEPTED/OFFER_REJECTED is the SUPPLIER's decision, not admin's (POST
# /organic-inputs/batches/{id}/procurement-offer/decision); OFFER_ACCEPTED ->
# RECEIVED needs a real BatchReceipt (POST .../receipt). None of those four are
# here for the same reason the QC transitions above aren't. RECEIVED onward is
# a plain admin judgement call with no required evidence record, so those
# three ARE listed below.
BATCH_ADMIN_DECISIONS: dict[BatchStatus, set[BatchStatus]] = {
    BatchStatus.SUBMITTED: {BatchStatus.UNDER_REVIEW},
    BatchStatus.UNDER_REVIEW: {
        BatchStatus.CLARIFICATION_REQUIRED,
        BatchStatus.INSPECTION_REQUIRED,
        BatchStatus.REJECTED,
    },
    BatchStatus.CLARIFICATION_REQUIRED: {BatchStatus.UNDER_REVIEW},
    BatchStatus.TESTING: {
        BatchStatus.RETEST_REQUIRED,
        BatchStatus.APPROVED,
        BatchStatus.PARTIALLY_APPROVED,
        BatchStatus.REJECTED,
    },
    BatchStatus.RECEIVED: {BatchStatus.QUARANTINED, BatchStatus.RELEASED_FOR_SALE},
    BatchStatus.QUARANTINED: {BatchStatus.RELEASED_FOR_SALE, BatchStatus.REJECTED},
    BatchStatus.RELEASED_FOR_SALE: {
        BatchStatus.SOLD_OUT,
        BatchStatus.EXPIRED,
        BatchStatus.RECALLED,
    },
}

class OfferStatus(StrEnum):
    """Status of a single AgrowAI-to-supplier procurement offer.

    A batch reaches PROCUREMENT_OFFERED/OFFER_ACCEPTED/OFFER_REJECTED at most
    once in this phase -- BATCH_TRANSITIONS has no edge back out of
    OFFER_REJECTED, so a rejected offer ends that batch's procurement path
    rather than looping into renegotiation. That is an existing constraint
    from the foundation phase, not a new one invented here.
    """

    OFFERED = "offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class InventoryMovementType(StrEnum):
    """Kinds of change to an InventoryLot.quantity_available.

    RECEIPT is written only by record_batch_receipt (system-generated, the
    lot's opening balance) -- ADJUSTMENT/WITHDRAWAL are the only types an
    admin can record directly via the inventory-adjustment endpoint. There is
    no SALE type yet: cart/orders don't exist in this repo (docs section 1),
    so a manual WITHDRAWAL is the honest stand-in for stock leaving inventory
    through whatever offline channel is actually moving it today.
    """

    RECEIPT = "receipt"
    ADJUSTMENT = "adjustment"
    WITHDRAWAL = "withdrawal"


# Inspection outcomes recorded on BatchInspection -- deliberately just
# pass/fail, entered by a human inspector; no auto-derivation from measurements.
INSPECTION_OUTCOMES = ("passed", "failed")

DOCUMENT_TYPES = (
    "identity_proof",
    "land_record",
    "license",
    "certification",
    "other",
)

BATCH_DOCUMENT_TYPES = (
    "photo",
    "lab_report",
    "license",
    "certification",
    "inspection_photo",
    "other",
)
