"""add secure admin web invitations

Revision ID: f12a6c7e9b10
Revises: e8c2f11a7d40
"""

import sqlalchemy as sa
from alembic import op
from app.shared.base_model import GUID

revision = "f12a6c7e9b10"
down_revision = "e8c2f11a7d40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    postgres = op.get_bind().dialect.name == "postgresql"
    with op.batch_alter_table("admin_users") as batch:
        batch.add_column(sa.Column("district_scope", sa.String(120), nullable=True))
        batch.create_index("ix_admin_users_district_scope", ["district_scope"])
    op.create_table(
        "admin_invitations",
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("district_scope", sa.String(120), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("invited_by_admin_id", GUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_user_id", GUID(), nullable=True),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["accepted_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["invited_by_admin_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_admin_invitations_email", "admin_invitations", ["email"])
    op.create_index(
        "ix_admin_invitations_invited_by_admin_id",
        "admin_invitations",
        ["invited_by_admin_id"],
    )
    if postgres:
        op.execute(
            "CREATE FUNCTION prevent_audit_log_mutation() RETURNS trigger AS $$ "
            "BEGIN RAISE EXCEPTION 'audit_logs are append-only'; END; $$ LANGUAGE plpgsql"
        )
        op.execute(
            "CREATE TRIGGER audit_logs_append_only BEFORE UPDATE OR DELETE ON audit_logs "
            "FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation()"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs")
        op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_mutation()")
    op.drop_index("ix_admin_invitations_invited_by_admin_id", table_name="admin_invitations")
    op.drop_index("ix_admin_invitations_email", table_name="admin_invitations")
    op.drop_table("admin_invitations")
    with op.batch_alter_table("admin_users") as batch:
        batch.drop_index("ix_admin_users_district_scope")
        batch.drop_column("district_scope")
