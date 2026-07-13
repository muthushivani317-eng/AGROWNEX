"""admin platform tables

Revision ID: 0018_admin_tables
Revises: 0017_memory_tables
Create Date: 2026-07-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_admin_tables"
down_revision: str | None = "0017_memory_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "admin_roles",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint("name", name="uq_admin_roles_name"),
    )

    op.create_table(
        "admin_permissions",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint("code", name="uq_admin_permissions_code"),
    )

    op.create_table(
        "admin_users",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("user_id", name="uq_admin_user"),
    )
    op.create_index("idx_admin_users_user", "admin_users", ["user_id"])
    op.create_index("idx_admin_users_role", "admin_users", ["role"])
    op.create_index("idx_admin_users_status", "admin_users", ["status"])

    op.create_table(
        "broadcast_messages",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("admin_id", UUID, sa.ForeignKey("admin_users.id"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="ta"),
        sa.Column("target_type", sa.String(16), nullable=False),
        sa.Column("target_value", sa.String(120), nullable=True),
        sa.Column("schedule_type", sa.String(12), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="draft"),
        sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_broadcasts_admin", "broadcast_messages", ["admin_id"])
    op.create_index("idx_broadcasts_status", "broadcast_messages", ["status"])

    op.create_table(
        "system_announcements",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("admin_id", UUID, sa.ForeignKey("admin_users.id"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="ta"),
        sa.Column("category", sa.String(40), nullable=True),
        sa.Column("audience", sa.String(12), nullable=False, server_default="all"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_announcements_admin", "system_announcements", ["admin_id"])
    op.create_index("idx_announcements_active", "system_announcements", ["is_active"])

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("admin_id", UUID, sa.ForeignKey("admin_users.id"), nullable=True),
        sa.Column("role", sa.String(40), nullable=True),
        sa.Column("action", sa.String(48), nullable=False),
        sa.Column("target", sa.String(48), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_audit_admin", "audit_logs", ["admin_id"])
    op.create_index("idx_audit_action", "audit_logs", ["action"])
    op.create_index("idx_audit_target", "audit_logs", ["target"])
    op.create_index("idx_audit_target_id", "audit_logs", ["target_id"])

    op.create_table(
        "dashboard_widgets",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("title_key", sa.String(80), nullable=False),
        sa.Column("widget_type", sa.String(20), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint("key", name="uq_dashboard_widget_key"),
    )

    op.create_table(
        "dashboard_preferences",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("admin_id", UUID, sa.ForeignKey("admin_users.id"), nullable=False),
        sa.Column("widget_key", sa.String(40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint("admin_id", "widget_key", name="uq_dashboard_pref"),
    )
    op.create_index("idx_dashboard_pref_admin", "dashboard_preferences", ["admin_id"])


def downgrade() -> None:
    op.drop_table("dashboard_preferences")
    op.drop_table("dashboard_widgets")
    op.drop_table("audit_logs")
    op.drop_table("system_announcements")
    op.drop_table("broadcast_messages")
    op.drop_table("admin_users")
    op.drop_table("admin_permissions")
    op.drop_table("admin_roles")
