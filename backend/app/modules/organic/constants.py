from enum import StrEnum


class OrganicFarmMode(StrEnum):
    CONVENTIONAL = "conventional"
    ORGANIC_PREFERRED = "organic_preferred"
    TRANSITIONING = "transitioning"
    FULLY_ORGANIC = "fully_organic"


class CertificationStatus(StrEnum):
    NOT_CLAIMED = "not_claimed"
    SELF_DECLARED = "self_declared"
    DOCUMENT_SUBMITTED = "document_submitted"
    VERIFIED = "verified"
    EXPIRED = "expired"
    REJECTED = "rejected"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
