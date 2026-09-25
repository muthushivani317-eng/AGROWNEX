"""Enforce audit_logs immutability at the database level.

Every write to audit_logs already only ever calls session.add(...) in
application code (no UPDATE/DELETE code path exists), but nothing at the
database level stopped a raw SQL script or direct DB console access from
altering or deleting a row. This adds a Postgres trigger that raises on
any UPDATE or DELETE against audit_logs, so the "one immutable audit
event per certification change" guarantee holds even outside the app.

SQLite (used by the test suite) has no equivalent trigger-function syntax
and is skipped here; the app-level insert-only discipline already covers
tests, and production is exclusively Postgres.

Revision ID: 10f4bbda5d11
Revises: f4b8d2a17c93
"""

from alembic import op

revision = "10f4bbda5d11"
down_revision = "f4b8d2a17c93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_logs_block_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs rows are immutable: % is not permitted', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_no_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_block_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_no_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_block_mutation();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update ON audit_logs;")
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_delete ON audit_logs;")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_block_mutation();")
