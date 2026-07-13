"""Auth module constants (docs/DATABASE_SCHEMA.md → User Domain)."""
from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class LoginMethod(StrEnum):
    PHONE = "phone"
    GOOGLE = "google"
    APPLE = "apple"


class RoleName(StrEnum):
    """Default roles (docs/DATABASE_SCHEMA.md → roles, docs/SECURITY.md → RBAC)."""

    FARMER = "farmer"
    FPO = "fpo"
    AGRICULTURE_OFFICER = "agriculture_officer"
    BUYER = "buyer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# OTP policy (docs/SECURITY.md → rate limiting, docs/DATABASE_SCHEMA.md → otp_requests).
OTP_LENGTH = 6
OTP_TTL_SECONDS = 300  # 5 minutes
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_WINDOW_SECONDS = 60  # min gap between sends to one number

# Refresh-token policy (docs/DATABASE_SCHEMA.md → refresh_tokens).
REFRESH_TOKEN_TTL_DAYS = 30
