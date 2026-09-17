"""Disposable-schema smoke test; not a substitute for a PostgreSQL staging rehearsal."""
from importlib import import_module

from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_organic_mvp_migration_preserves_existing_diary_row():
    engine = create_engine("sqlite:///:memory:")
    migration = import_module("migrations.versions.c9f412a7e60b_organic_pilot_mvp")
    partner_migration = import_module("migrations.versions.a4d8f21b6c90_organic_partner_access")
    original_op = migration.op
    original_partner_op = partner_migration.op
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE organic_practice_log_entries (id VARCHAR(36) PRIMARY KEY, notes TEXT)"
            ))
            connection.execute(text(
                "INSERT INTO organic_practice_log_entries (id, notes) VALUES ('legacy-row', 'keep me')"
            ))
            migration.op = Operations(MigrationContext.configure(connection))
            partner_migration.op = migration.op
            migration.upgrade()
            partner_migration.upgrade()
            assert "organic_pgs_cases" in inspect(connection).get_table_names()
            assert "organic_partner_farmer_links" in inspect(connection).get_table_names()
            columns = {item["name"] for item in inspect(connection).get_columns("organic_practice_log_entries")}
            assert {"expense_amount_inr", "voice_transcript"} <= columns
            assert connection.execute(text(
                "SELECT notes FROM organic_practice_log_entries WHERE id='legacy-row'"
            )).scalar_one() == "keep me"
            partner_migration.downgrade()
            migration.downgrade()
            assert "organic_pgs_cases" not in inspect(connection).get_table_names()
            assert "organic_partner_farmer_links" not in inspect(connection).get_table_names()
            assert connection.execute(text(
                "SELECT notes FROM organic_practice_log_entries WHERE id='legacy-row'"
            )).scalar_one() == "keep me"
    finally:
        migration.op = original_op
        partner_migration.op = original_partner_op
        engine.dispose()
