"""Global exception handlers → standard error envelope (docs/API_CONTRACT.md).

Registered on the FastAPI app so every failure returns the documented shape with
a request id, and unexpected errors are logged (never swallowed).
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.schemas.response import ErrorResponse, FieldError

logger = get_logger("api.errors")


def _request_id(request: Request) -> str:
    # Prefer the id assigned by RequestIDMiddleware; fall back to an inbound header.
    rid = getattr(request.state, "request_id", "")
    return rid or request.headers.get("X-Request-ID", "")


def _envelope(
    request: Request,
    *,
    status_code: int,
    message: str,
    error_code: str,
    errors: list[FieldError] | None = None,
    headers: dict[str, str] | None = None,
    details: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        message=message,
        error_code=error_code,
        errors=errors or [],
        details=details,
        request_id=_request_id(request),
    )
    return JSONResponse(
        status_code=status_code,
        # Optional diagnostic details are part of the contract only when an
        # AppError actually supplies them; do not add a new `details: null`
        # key to every existing HTTP error response.
        content=body.model_dump(exclude_none=True),
        headers=headers,
    )


def _is_database_unavailable(exc: BaseException) -> bool:
    """Connection refused/dropped or connection-pool exhausted."""
    from sqlalchemy.exc import DisconnectionError, InterfaceError, OperationalError
    from sqlalchemy.exc import TimeoutError as PoolTimeoutError

    seen = 0
    while exc is not None and seen < 5:  # walk __cause__ chain (driver errors are wrapped)
        if isinstance(exc, OperationalError | InterfaceError | DisconnectionError | PoolTimeoutError):
            return True
        if isinstance(exc, ConnectionRefusedError | ConnectionResetError):
            return True
        exc = exc.__cause__ or exc.__context__
        seen += 1
    return False


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        code = detail.get("code")
        message = detail.get("message")
        if not isinstance(code, str) or not code:
            code = "http_error"
        if not isinstance(message, str) or not message:
            message = "The request could not be completed."
        return _envelope(
            request,
            status_code=exc.status_code,
            message=message,
            error_code=code,
            headers=exc.headers,
        )

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return _envelope(
            request,
            status_code=exc.status_code,
            message=exc.message,
            error_code=exc.error_code,
            details=getattr(exc, "details", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            FieldError(field=".".join(str(p) for p in e["loc"]), message=e["msg"])
            for e in exc.errors()
        ]
        return _envelope(
            request,
            status_code=422,
            message="Validation failed.",
            error_code="validation_error",
            errors=errors,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        if _is_database_unavailable(exc):
            # Outage, not a bug: tell the app to retry (it shows "try again"),
            # and keep these distinct from real 500s in monitoring.
            logger.error("Database unavailable: %s", type(exc).__name__)
            return _envelope(
                request,
                status_code=503,
                message="Service is temporarily unavailable. Please try again.",
                error_code="SERVICE_TEMPORARILY_UNAVAILABLE",
                headers={"Retry-After": "10"},
            )
        logger.exception("Unhandled error: %s", type(exc).__name__)
        return _envelope(
            request,
            status_code=500,
            message="An unexpected error occurred.",
            error_code="internal_error",
        )
