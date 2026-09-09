from app.core.exceptions import NotFoundError, ValidationError


class OrganicLogEntryNotFoundError(NotFoundError):
    error_code = "organic_log_entry_not_found"
    message = "Organic practice log entry not found."


class OrganicLogReferenceError(ValidationError):
    error_code = "organic_log_reference_invalid"
    message = "The referenced task or action is not valid for this farm."
