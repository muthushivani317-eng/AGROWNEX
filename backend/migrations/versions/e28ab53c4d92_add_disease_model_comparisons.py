"""add controlled disease model comparisons

Revision ID: e28ab53c4d92
Revises: d12eb863ff71
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e28ab53c4d92"
down_revision = "d12eb863ff71"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "disease_model_comparisons",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("image_sha256", sa.String(64), nullable=False),
        sa.Column("crop", sa.String(40), nullable=False),
        sa.Column("local_model", sa.String(120), nullable=False),
        sa.Column("local_status", sa.String(40), nullable=False),
        sa.Column("local_label", sa.String(120)),
        sa.Column("local_confidence", sa.Float()),
        sa.Column("provider", sa.String(40), server_default="openai", nullable=False),
        sa.Column("provider_model", sa.String(120), nullable=False),
        sa.Column("provider_status", sa.String(40), nullable=False),
        sa.Column("provider_label", sa.String(120)),
        sa.Column("crop_assessment", sa.String(20)),
        sa.Column("assessment_status", sa.String(24)),
        sa.Column("alternative_labels", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("visual_observations", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("agrees_with_local", sa.Boolean()),
        sa.Column("error_code", sa.String(80)),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("test_mode", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("exposed_to_farmer", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    for column in ("user_id", "image_sha256", "crop", "provider_status"):
        op.create_index(
            f"ix_disease_model_comparisons_{column}", "disease_model_comparisons", [column]
        )


def downgrade() -> None:
    op.drop_table("disease_model_comparisons")
