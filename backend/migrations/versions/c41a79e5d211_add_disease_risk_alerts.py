"""Add persisted disease-risk alert workflow.

Revision ID: c41a79e5d211
Revises: a341fd7820cc
"""
import sqlalchemy as sa
from alembic import op

revision = "c41a79e5d211"
down_revision = "a341fd7820cc"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("disease_risk_alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("farm_id", sa.Uuid(), sa.ForeignKey("farms.id"), nullable=False, index=True),
        sa.Column("crop", sa.String(80), nullable=False), sa.Column("disease_key", sa.String(100)),
        sa.Column("status", sa.String(50), nullable=False, index=True), sa.Column("risk_level", sa.String(20)),
        sa.Column("confidence", sa.String(30), nullable=False), sa.Column("weather_factors", sa.JSON(), nullable=False),
        sa.Column("weather_source", sa.String(20), nullable=False), sa.Column("weather_observed_at", sa.DateTime(timezone=True)),
        sa.Column("crop_stage", sa.String(30)), sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True)), sa.Column("rule_pack_id", sa.String(100)),
        sa.Column("rule_version", sa.String(40)), sa.Column("rule_verification_status", sa.String(30), nullable=False),
        sa.Column("farmer_message_key", sa.String(100), nullable=False), sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("missing_inputs", sa.JSON(), nullable=False), sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("idempotency_key", sa.String(100), nullable=False), sa.Column("notification_emitted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_disease_risk_user_key"))

def downgrade() -> None:
    op.drop_table("disease_risk_alerts")
