"""Global exception handlers → standard error envelope (docs/API_CONTRACT.md).

Registered on the FastAPI app so every failure returns the documented shape with
a request id, and unexpected errors are logged (never swallowed).
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.schemas.response import ErrorResponse, FieldError

logger = get_logger("api.errors")


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", "")


def _envelope(
    request: Request,
    *,
    status_code: int,
    message: str,
    error_code: str,
    errors: list[FieldError] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        message=message,
        error_code=error_code,
        errors=errors or [],
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return _envelope(
            request,
            status_code=exc.status_code,
            message=exc.message,
            error_code=exc.error_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
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
        logger.exception("Unhandled error: %s", type(exc).__name__)
        return _envelope(
            request,
            status_code=500,
            message="An unexpected error occurred.",
            error_code="internal_error",
        )
