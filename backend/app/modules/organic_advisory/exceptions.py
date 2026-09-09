from app.core.exceptions import NotFoundError, ValidationError


class OrganicAdvisoryReferenceError(NotFoundError):
    error_code = "organic_advisory_reference_not_found"
    message = "The referenced organic action or observation was not found."


class OrganicAdvisoryNotAllowedError(ValidationError):
    error_code = "organic_advisory_not_allowed"
    message = "This recommendation is not supported by approved guidance and evidence."
