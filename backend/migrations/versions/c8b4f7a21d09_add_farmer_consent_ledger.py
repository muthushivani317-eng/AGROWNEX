"""add immutable user consent ledger

Revision ID: c8b4f7a21d09
Revises: e2b7a4c19f01
"""

import sqlalchemy as sa
from alembic import op
from app.shared.base_model import GUID

revision = "c8b4f7a21d09"
down_revision = "e2b7a4c19f01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_consent_states",
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("last_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "purpose"),
    )
    op.create_table(
        "user_consent_events",
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("notice_hash", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("locale", sa.String(10), nullable=False),
        sa.Column("id", GUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "purpose", "version", name="uq_consent_user_purpose_version"
        ),
        sa.UniqueConstraint("user_id", "purpose", "idempotency_key", name="uq_consent_idempotency"),
    )
    op.create_index("ix_user_consent_events_user_id", "user_consent_events", ["user_id"])
    op.create_index("ix_user_consent_events_purpose", "user_consent_events", ["purpose"])
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("""CREATE FUNCTION reject_consent_event_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'CONSENT_EVENT_IMMUTABLE'; END; $$ LANGUAGE plpgsql""")
        op.execute("""CREATE TRIGGER user_consent_events_immutable BEFORE UPDATE OR DELETE
        ON user_consent_events FOR EACH ROW EXECUTE FUNCTION reject_consent_event_mutation()""")
    elif dialect == "sqlite":
        op.execute(
            "CREATE TRIGGER user_consent_events_no_update "
            "BEFORE UPDATE ON user_consent_events "
            "BEGIN SELECT RAISE(ABORT, 'CONSENT_EVENT_IMMUTABLE'); END"
        )
        op.execute(
            "CREATE TRIGGER user_consent_events_no_delete "
            "BEFORE DELETE ON user_consent_events "
            "BEGIN SELECT RAISE(ABORT, 'CONSENT_EVENT_IMMUTABLE'); END"
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS user_consent_events_immutable ON user_consent_events")
        op.execute("DROP FUNCTION IF EXISTS reject_consent_event_mutation()")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS user_consent_events_no_update")
        op.execute("DROP TRIGGER IF EXISTS user_consent_events_no_delete")
    op.drop_index("ix_user_consent_events_purpose", table_name="user_consent_events")
    op.drop_index("ix_user_consent_events_user_id", table_name="user_consent_events")
    op.drop_table("user_consent_events")
    op.drop_table("user_consent_states")
