from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.modules.auth.models import User
from app.modules.farms.exceptions import FarmNotFoundError
from app.modules.farms.models import Farm
from app.modules.organic.governance import input_hash_is_valid
from app.modules.organic.ingestion import (
    OrganicInputManifest,
    ingest_versioned_input,
    seed_public_source_pack,
)
from app.modules.organic.router import router
from app.modules.organic.schemas import OrganicProfileWrite
from app.modules.organic.service import OrganicService
from app.modules.organic_logbook.models import OrganicPracticeLogEntry


async def _user(session, uid: str, phone: str):
    row = User(
        firebase_uid=uid,
        phone_number=phone,
        email=None,
        is_phone_verified=True,
        is_email_verified=False,
        status="active",
    )
    session.add(row)
    await session.flush()
    return row


async def test_summary_empty_state_and_ownership(db_session):
    owner = await _user(db_session, "summary-owner", "+919000000201")
    other = await _user(db_session, "summary-other", "+919000000202")
    farm = Farm(user_id=owner.id, name="Summary farm")
    db_session.add(farm)
    await db_session.flush()
    service = OrganicService(db_session)

    summary = await service.farm_summary(owner, farm.id)
    assert summary == {
        "farm_id": farm.id,
        "profile": None,
        "certification_status": None,
        "certification_verified": False,
        "soil_plan_available": False,
        "pending_organic_actions": 0,
        "logbook_entries": 0,
        "weather_advisory_available": False,
        "satellite_advisory_available": False,
        "traceability_ready": False,
        "traceability_batch_count": 0,
    }
    with pytest.raises(FarmNotFoundError):
        await service.farm_summary(other, farm.id)


async def test_organic_plan_bundle_matches_mobile_contract(db_session):
    owner = await _user(db_session, "plan-owner", "+919000000205")
    farm = Farm(user_id=owner.id, name="Plan farm")
    db_session.add(farm)
    await db_session.flush()
    bundle = await OrganicService(db_session).farm_plan(owner, farm.id)
    assert bundle["farm_id"] == farm.id
    assert bundle["generated_at"].tzinfo is not None
    assert bundle["actions"] == []


async def test_traceability_readiness_requires_profile_and_real_log_entry(db_session):
    owner = await _user(db_session, "ready-owner", "+919000000203")
    farm = Farm(user_id=owner.id, name="Ready farm")
    db_session.add(farm)
    await db_session.flush()
    service = OrganicService(db_session)
    await service.upsert_profile(
        owner,
        farm.id,
        OrganicProfileWrite(mode="organic_preferred"),
        "summary-profile-001",
    )
    db_session.add(
        OrganicPracticeLogEntry(
            user_id=owner.id,
            farm_id=farm.id,
            practice_type="compost",
            practice_code="compost_applied",
            occurred_at=datetime.now(UTC),
            outcome_status="not_reported",
            source_feature="manual_logbook",
            source_record_id="manual-1",
            source_version="farmer-v1",
            source_verified=False,
            verification_status="farmer_reported",
            expert_reviewed=False,
            idempotency_key="summary-log-001",
        )
    )
    await db_session.flush()
    summary = await service.farm_summary(owner, farm.id)
    assert summary["logbook_entries"] == 1
    assert summary["traceability_ready"] is True
    assert summary["certification_verified"] is False


async def test_offline_ingestion_requires_operator_review_and_is_immutable(db_session):
    reviewer = await _user(db_session, "content-reviewer", "+919000000204")
    manifest = OrganicInputManifest(
        slug="reviewed-neem-input",
        category="botanical",
        name_en="Reviewed neem input",
        name_ta="மதிப்பாய்வு செய்யப்பட்ட வேம்பு உள்ளீடு",
        purpose_en="Reviewed purpose",
        purpose_ta="மதிப்பாய்வு செய்யப்பட்ட நோக்கம்",
        guidance={"target_diseases": ["leaf_spot"]},
        applicable_crops=["paddy"],
        applicable_regions=["Tamil Nadu"],
        source_organization="TNAU",
        document_reference="Guide 2026",
        source_url="https://example.invalid/guide-2026",
        source_version="2026.1",
        review_status="approved",
        reviewed_by=reviewer.id,
        reviewed_at=datetime.now(UTC),
    )
    row = await ingest_versioned_input(db_session, manifest)
    assert input_hash_is_valid(row)
    with pytest.raises(ValueError, match="VERSION_ALREADY_EXISTS"):
        await ingest_versioned_input(db_session, manifest)


def test_approved_manifest_without_operator_review_is_rejected():
    with pytest.raises(ValueError, match="reviewed_by"):
        OrganicInputManifest(
            slug="unreviewed-input",
            category="compost",
            name_en="Unreviewed",
            name_ta="மதிப்பாய்வு செய்யப்படாதது",
            purpose_en="No review",
            purpose_ta="மதிப்பாய்வு இல்லை",
            guidance={},
            source_organization="TNAU",
            document_reference="Draft",
            source_url="https://example.invalid/draft",
            source_version="draft-1",
            review_status="approved",
        )


def test_farmer_router_has_no_input_publish_endpoint():
    input_write_routes = [
        route
        for route in router.routes
        if route.path.startswith("/organic-inputs")
        and bool(set(route.methods or ()) & {"POST", "PUT", "PATCH", "DELETE"})
    ]
    assert input_write_routes == []


async def test_public_source_pack_is_bilingual_and_fails_closed_until_promoted(db_session):
    created = await seed_public_source_pack(db_session)
    assert len(created) >= 2
    assert all(row.review_status == "sourced_public_reference" for row in created)
    assert all(row.name_en and row.name_ta and row.purpose_en and row.purpose_ta for row in created)
    assert all(input_hash_is_valid(row) for row in created)
    assert all(not row.guidance.get("target_diseases") for row in created)
    assert all(not row.limitations.get("application_rates") for row in created)

    approved, total = await OrganicService(db_session).list_inputs(
        category=None, crop=None, search=None, page=1, page_size=100
    )
    assert approved == [] and total == 0
    coverage = await OrganicService(db_session).catalogue_coverage()
    assert coverage["awaiting_human_review"] == len(created)
    assert coverage["approved"] == 0

    assert await seed_public_source_pack(db_session) == []
