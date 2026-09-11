from app.core.exceptions import ConflictError, NotFoundError, ValidationError


class CatalogItemUnavailableError(ConflictError):
    error_code = "input_catalog_item_unavailable"
    message = "An item is unavailable or out of stock. Refresh the catalog."


class StaleCatalogPriceError(ConflictError):
    error_code = "input_catalog_price_changed"
    message = "An item price changed. Refresh the catalog before ordering."


class InputOrderNotFoundError(NotFoundError):
    error_code = "input_order_not_found"
    message = "Order not found."


class InvalidOrderTransitionError(ValidationError):
    error_code = "invalid_input_order_transition"
    message = "That order status change is not allowed."
