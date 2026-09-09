from app.core.exceptions import ConflictError, NotFoundError, ValidationError


class OrganicProfileNotFoundError(NotFoundError):
    error_code = "organic_profile_not_found"
    message = "Organic farm profile not found."


class OrganicInputNotFoundError(NotFoundError):
    error_code = "organic_input_not_found"
    message = "Approved organic input not found."


class OrganicSourceGovernanceError(ValidationError):
    error_code = "organic_source_not_approved"
    message = "Organic guidance is unavailable because its source approval is missing or expired."


class InvalidCertificationUploadError(ValidationError):
    error_code = "invalid_certification_upload_receipt"
    message = "Certification document upload could not be verified."


class VerifiedCertificationLockedError(ConflictError):
    error_code = "verified_certification_locked"
    message = "Verified certification fields can only be changed by an authorized reviewer."
