"""Organic pilot workflow tables, joining the two existing migration heads.

Revision ID: c9f412a7e60b
Revises: c91a4e7d2f10, d1a9f4c8b2e7, e6b7c81f2a10
"""
from alembic import op
import sqlalchemy as sa

from app.shared.base_model import GUID

revision = "c9f412a7e60b"
down_revision = ("c91a4e7d2f10", "d1a9f4c8b2e7", "e6b7c81f2a10")
branch_labels = None
depends_on = None


def _base():
    return [
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _id(name, target, nullable=False):
    return sa.Column(name, GUID(), sa.ForeignKey(target), nullable=nullable)


def upgrade():
    op.add_column("organic_practice_log_entries", sa.Column("expense_amount_inr", sa.Numeric(12, 2)))
    op.add_column("organic_practice_log_entries", sa.Column("voice_transcript", sa.Text()))
    op.create_table("organic_fpos", *_base(),
        sa.Column("name", sa.String(180), nullable=False), sa.Column("district", sa.String(80), nullable=False),
        sa.Column("registration_reference", sa.String(120)), sa.Column("is_test", sa.Boolean(), nullable=False))
    op.create_table("organic_pilots", *_base(),
        _id("fpo_id", "organic_fpos.id", True),
        sa.Column("fpo_name", sa.String(180)), sa.Column("district", sa.String(80)),
        sa.Column("crop_ids", sa.JSON(), nullable=False), _id("agronomist_user_id", "users.id", True),
        sa.Column("certification_pathway", sa.String(24)),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("is_test", sa.Boolean(), nullable=False))
    op.create_table("organic_pilot_enrollments", *_base(),
        _id("pilot_id", "organic_pilots.id"), _id("farm_id", "farms.id"), _id("farmer_user_id", "users.id"),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("pilot_id", "farm_id", name="uq_organic_pilot_farm"))
    op.create_table("organic_plots", *_base(), _id("farm_id", "farms.id"),
        sa.Column("name", sa.String(120), nullable=False), sa.Column("area_hectares", sa.Float()),
        sa.Column("boundary_geojson", sa.JSON()), sa.Column("trial_only", sa.Boolean(), nullable=False))
    op.create_table("organic_crop_cycles", *_base(), _id("plot_id", "organic_plots.id"),
        sa.Column("crop_id", sa.String(80), nullable=False), sa.Column("sowing_date", sa.Date()),
        sa.Column("expected_harvest_start", sa.Date()), sa.Column("expected_harvest_end", sa.Date()),
        sa.Column("expected_quantity_kg", sa.Float()), sa.Column("source", sa.String(24), nullable=False))
    op.create_table("organic_readiness_rules", *_base(),
        sa.Column("version", sa.String(60), nullable=False, unique=True),
        sa.Column("questions", sa.JSON(), nullable=False), sa.Column("scoring", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False), _id("approved_by", "users.id", True),
        sa.Column("approved_at", sa.DateTime(timezone=True)))
    op.create_table("organic_readiness_assessments", *_base(),
        _id("farm_id", "farms.id"), _id("farmer_user_id", "users.id"),
        sa.Column("answers", sa.JSON(), nullable=False), sa.Column("rules_version", sa.String(60)),
        sa.Column("score", sa.Integer()), sa.Column("pathway", sa.String(40), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False))
    op.create_table("organic_task_templates", *_base(),
        sa.Column("crop_id", sa.String(80), nullable=False), sa.Column("district", sa.String(80), nullable=False),
        sa.Column("version", sa.String(60), nullable=False), sa.Column("tasks", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False), _id("agronomist_user_id", "users.id", True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("review_note", sa.Text()),
        sa.UniqueConstraint("crop_id", "district", "version", name="uq_organic_template_version"))
    op.create_table("organic_scheduled_tasks", *_base(),
        _id("crop_cycle_id", "organic_crop_cycles.id"), _id("template_id", "organic_task_templates.id"),
        sa.Column("day_offset", sa.Integer(), nullable=False), sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("title_ta", sa.String(240), nullable=False), sa.Column("body_ta", sa.Text(), nullable=False),
        sa.Column("title_en", sa.String(240)), sa.Column("body_en", sa.Text()),
        sa.Column("status", sa.String(24), nullable=False))
    op.create_table("organic_pgs_cases", *_base(),
        _id("farm_id", "farms.id"), _id("farmer_user_id", "users.id"),
        sa.Column("state", sa.String(50), nullable=False), sa.Column("partial_conversion", sa.Boolean(), nullable=False),
        sa.Column("checklist", sa.JSON(), nullable=False), sa.Column("regional_council_approval_ref", sa.String(180)),
        sa.Column("certificate_id", sa.String(160)), sa.Column("issuing_authority", sa.String(180)),
        _id("certificate_document_id", "organic_certification_documents.id", True),
        sa.Column("valid_from", sa.Date()), sa.Column("valid_to", sa.Date()),
        _id("verified_by", "users.id", True), sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("non_compliance_note", sa.Text()), sa.UniqueConstraint("farm_id", name="uq_organic_pgs_farm"))
    op.create_table("organic_peer_appraisals", *_base(),
        _id("case_id", "organic_pgs_cases.id"), sa.Column("scheduled_on", sa.Date(), nullable=False),
        _id("peer_user_id", "users.id", True), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("findings", sa.JSON()), sa.Column("completed_at", sa.DateTime(timezone=True)))
    for table, column in (("organic_pilot_enrollments", "pilot_id"), ("organic_pilot_enrollments", "farm_id"),
                          ("organic_plots", "farm_id"), ("organic_crop_cycles", "plot_id"),
                          ("organic_readiness_assessments", "farm_id"),
                          ("organic_scheduled_tasks", "crop_cycle_id"), ("organic_peer_appraisals", "case_id")):
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for table in ("organic_peer_appraisals", "organic_pgs_cases", "organic_scheduled_tasks",
                  "organic_task_templates", "organic_readiness_assessments", "organic_readiness_rules",
                  "organic_crop_cycles", "organic_plots", "organic_pilot_enrollments", "organic_pilots", "organic_fpos"):
        op.drop_table(table)
    op.drop_column("organic_practice_log_entries", "voice_transcript")
    op.drop_column("organic_practice_log_entries", "expense_amount_inr")
