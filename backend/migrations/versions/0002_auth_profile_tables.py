"""auth session, rbac and farmer profile tables

Revision ID: 0002_auth_profile_tables
Revises: 0001_create_users
Create Date: 2026-07-08
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_auth_profile_tables"
down_revision: str | None = "0001_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def _pk() -> sa.Column:
    return sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _timestamps() -> list[sa.Column]:
    now = sa.func.now()
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    ]


def _soft_delete() -> list[sa.Column]:
    return [
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    ]


def upgrade() -> None:
    # --- otp_requests ---
    op.create_table(
        "otp_requests",
        _pk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("otp_hash", sa.String(128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
    )
    op.create_index("idx_otp_requests_phone", "otp_requests", ["phone_number"])
    op.create_index("idx_otp_requests_user", "otp_requests", ["user_id"])
    op.create_index("idx_otp_requests_expires", "otp_requests", ["expires_at"])

    # --- refresh_tokens ---
    op.create_table(
        "refresh_tokens",
        _pk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_id", sa.String(128), nullable=True),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
    )
    op.create_unique_constraint("uq_refresh_token_hash", "refresh_tokens", ["token_hash"])
    op.create_index("idx_refresh_tokens_user", "refresh_tokens", ["user_id"])

    # --- user_sessions ---
    op.create_table(
        "user_sessions",
        _pk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_name", sa.String(120), nullable=True),
        sa.Column("device_type", sa.String(40), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
    )
    op.create_index("idx_user_sessions_user", "user_sessions", ["user_id"])

    # --- login_history ---
    op.create_table(
        "login_history",
        _pk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("login_method", sa.String(20), nullable=False),
        sa.Column("device", sa.String(120), nullable=True),
        sa.Column("platform", sa.String(40), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
    )
    op.create_index("idx_login_history_user", "login_history", ["user_id"])

    # --- roles / permissions / role_permissions / user_roles ---
    roles_table = op.create_table(
        "roles",
        _pk(),
        sa.Column("role_name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        *_timestamps(),
    )
    op.create_unique_constraint("uq_roles_name", "roles", ["role_name"])

    # Seed default roles (docs/DATABASE_SCHEMA.md → roles; docs/SECURITY.md → RBAC).
    op.bulk_insert(
        roles_table,
        [
            {"role_name": "farmer", "description": "Farmer (default)"},
            {"role_name": "fpo", "description": "Farmer Producer Organization"},
            {"role_name": "agriculture_officer", "description": "Agriculture officer"},
            {"role_name": "buyer", "description": "Buyer"},
            {"role_name": "admin", "description": "Administrator"},
            {"role_name": "super_admin", "description": "Super administrator"},
        ],
    )

    op.create_table(
        "permissions",
        _pk(),
        sa.Column("permission_name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        *_timestamps(),
    )
    op.create_unique_constraint("uq_permissions_name", "permissions", ["permission_name"])

    op.create_table(
        "role_permissions",
        _pk(),
        sa.Column("role_id", UUID, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("permission_id", UUID, sa.ForeignKey("permissions.id"), nullable=False),
        *_timestamps(),
    )
    op.create_unique_constraint(
        "uq_role_permission", "role_permissions", ["role_id", "permission_id"]
    )
    op.create_index("idx_role_permissions_role", "role_permissions", ["role_id"])

    op.create_table(
        "user_roles",
        _pk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", UUID, sa.ForeignKey("roles.id"), nullable=False),
        *_timestamps(),
    )
    op.create_unique_constraint("uq_user_role", "user_roles", ["user_id", "role_id"])
    op.create_index("idx_user_roles_user", "user_roles", ["user_id"])

    # --- farmer_profiles / farmer_preferences / farmer_languages ---
    op.create_table(
        "farmer_profiles",
        _pk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("language", sa.String(5), nullable=False, server_default="ta"),
        sa.Column("district", sa.String(80), nullable=True),
        sa.Column("block", sa.String(80), nullable=True),
        sa.Column("village", sa.String(80), nullable=True),
        sa.Column("profile_photo", sa.String(512), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("education", sa.String(80), nullable=True),
        sa.Column("primary_crop", sa.String(80), nullable=True),
        sa.Column("secondary_crop", sa.String(80), nullable=True),
        *_timestamps(),
        *_soft_delete(),
    )
    op.create_unique_constraint("uq_farmer_profiles_user", "farmer_profiles", ["user_id"])
    op.create_index("idx_farmer_profiles_district", "farmer_profiles", ["district"])
    op.create_index("idx_farmer_profiles_primary_crop", "farmer_profiles", ["primary_crop"])

    op.create_table(
        "farmer_preferences",
        _pk(),
        sa.Column("farmer_id", UUID, sa.ForeignKey("farmer_profiles.id"), nullable=False),
        sa.Column("theme", sa.String(10), nullable=False, server_default="system"),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("voice_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("preferred_units", sa.String(20), nullable=False, server_default="metric"),
        sa.Column("default_crop", sa.String(80), nullable=True),
        *_timestamps(),
    )
    op.create_unique_constraint(
        "uq_farmer_preferences_farmer", "farmer_preferences", ["farmer_id"]
    )

    op.create_table(
        "farmer_languages",
        _pk(),
        sa.Column("farmer_id", UUID, sa.ForeignKey("farmer_profiles.id"), nullable=False),
        sa.Column("language_code", sa.String(5), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
    )
    op.create_index("idx_farmer_languages_farmer", "farmer_languages", ["farmer_id"])


def downgrade() -> None:
    op.drop_table("farmer_languages")
    op.drop_table("farmer_preferences")
    op.drop_table("farmer_profiles")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("login_history")
    op.drop_table("user_sessions")
    op.drop_table("refresh_tokens")
    op.drop_table("otp_requests")
