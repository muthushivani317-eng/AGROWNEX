import importlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.organic.certification_receipt import (
    CERTIFICATION_DOCUMENT,
    LOGBOOK_EVIDENCE,
    store_and_attest_upload,
    upload_receipt_is_valid,
)
from app.shared.base_model import Base


class RecordingStorage:
    def __init__(self):
        self.keys = []

    async def put(self, *, key, data, content_type):
        self.keys.append((key, data, content_type))
        return f"https://private.invalid/{key}"


class AssigningSession:
    def __init__(self):
        self.row = None

    def add(self, row):
        row.id = uuid.uuid4()
        self.row = row

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_attestation_is_versioned_expiring_and_purpose_bound():
    now = datetime.now(UTC)
    user_id, farm_id = uuid.uuid4(), uuid.uuid4()
    session, storage = AssigningSession(), RecordingStorage()
    row, receipt = await store_and_attest_upload(
        session,
        storage,
        user_id=user_id,
        farm_id=farm_id,
        purpose=CERTIFICATION_DOCUMENT,
        data=b"certificate",
        mime_type="application/pdf",
        file_suffix="pdf",
        now=now,
    )

    assert row.object_version in row.object_key
    assert upload_receipt_is_valid(
        attestation=row,
        user_id=user_id,
        farm_id=farm_id,
        purpose=CERTIFICATION_DOCUMENT,
        receipt=receipt,
        now=now,
    )
    assert not upload_receipt_is_valid(
        attestation=row,
        user_id=user_id,
        farm_id=farm_id,
        purpose=LOGBOOK_EVIDENCE,
        receipt=receipt,
        now=now,
    )
    assert not upload_receipt_is_valid(
        attestation=row,
        user_id=user_id,
        farm_id=farm_id,
        purpose=CERTIFICATION_DOCUMENT,
        receipt=receipt,
        now=now + timedelta(hours=1),
    )


def test_attestation_model_and_migration_chain_are_registered():
    migration = importlib.import_module(
        "migrations.versions.d4f8b61e2c90_add_organic_upload_attestations"
    )
    assert migration.down_revision == "c2e7a49d8b31"
    table = Base.metadata.tables["organic_upload_attestations"]
    assert {"purpose", "object_version", "issued_at", "expires_at"} <= set(
        table.columns.keys()
    )
    assert (
        "upload_attestation_id" in Base.metadata.tables["organic_certification_documents"].columns
    )
    assert "upload_attestation_id" in Base.metadata.tables["organic_practice_evidence"].columns
