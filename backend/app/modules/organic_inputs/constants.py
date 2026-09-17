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
}

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
