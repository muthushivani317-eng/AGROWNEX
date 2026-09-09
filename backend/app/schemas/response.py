"""Standard API envelope (docs/API_CONTRACT.md).

Every response — success or error — is wrapped in one of these shapes so all
clients (mobile, admin, future portals) can parse responses uniformly.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: T | None = None
    timestamp: str = Field(default_factory=_now_iso)
    request_id: str = ""


class FieldError(BaseModel):
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str
    errors: list[FieldError] = Field(default_factory=list)
    # Optional small string map giving a client enough structure to build a
    # more specific, localized message than `message` alone (e.g. which crop
    # was expected vs observed on a nutrient-analysis crop mismatch). Absent
    # for the vast majority of errors -- never anything sensitive.
    details: dict[str, str] | None = None
    timestamp: str = Field(default_factory=_now_iso)
    request_id: str = ""


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int


def success(
    data: T | None = None, message: str = "Success", request_id: str = ""
) -> SuccessResponse[T]:
    return SuccessResponse(data=data, message=message, request_id=request_id)
