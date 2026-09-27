from datetime import date, timedelta

import pytest

from app.core.exceptions import ValidationError
from app.modules.organic_mvp.common_plan import COMMON_PLAN_VERSION, build_common_plan
from app.modules.organic_mvp.engine import (
    TRIAL_NOTICE, forecast_gate, schedule_reviewed_tasks, score_readiness,
    validate_pgs_transition,
)
from app.modules.organic_mvp import models as _organic_mvp_models  # noqa: F401
from app.modules.organic_mvp.router import (
    add_crop_cycle, add_plot, crop_plan, pgs_status, review_pgs, setup_status, today_task,
    update_pgs_checklist,
    admin_pgs_review_queue,
)
from app.modules.organic_mvp.schemas import CropCycleIn, PgsFarmerIn, PgsReviewIn, PlotIn
from app.modules.auth.models import User
from app.modules.admin.constants import AdminPermission, AdminRole
from app.modules.admin.models import AdminUser, AuditLog
from app.modules.admin.service import AdminContext
from app.modules.farms.models import Farm
from sqlalchemy import select


def test_trial_is_explicitly_not_certified():
    assert TRIAL_NOTICE == "Pre-certification trial—not PGS certified."


def test_readiness_uses_only_configured_scoring():
    rules = {"questions": [{"id": "water", "options": {"yes": {"points": 2}, "no": {"points": 0, "risk_flag": "water"}}}],
             "bands": [{"min": 0, "max": 100, "pathway": "learning", "recommendation_ta": "கற்றல்"}]}
    assert score_readiness({"water": "no"}, rules)["risk_flags"] == ["water"]
    with pytest.raises(ValidationError):
        score_readiness({}, rules)


def test_pgs_claim_requires_valid_external_evidence():
    with pytest.raises(ValidationError):
        validate_pgs_transition(requested="pgs_organic", partial_conversion=False,
            council_approval_ref=None, certificate_id="x", issuing_authority="council",
            valid_from=date(2025, 1, 1), valid_to=date(2030, 1, 1),
            verified=False, major_non_compliance=False)
    with pytest.raises(ValidationError):
        validate_pgs_transition(requested="pgs_green_under_conversion", partial_conversion=True,
            council_approval_ref=None, certificate_id="x", issuing_authority="council",
            valid_from=date(2025, 1, 1), valid_to=date(2030, 1, 1),
            verified=True, major_non_compliance=False)


def test_plan_is_bounded_and_requires_tamil():
    with pytest.raises(ValidationError):
        schedule_reviewed_tasks([{"day_offset": 401, "title_ta": "x", "body_ta": "y"}], date(2026, 1, 1))
    with pytest.raises(ValidationError):
        schedule_reviewed_tasks([{"day_offset": 1, "title_en": "English"}], date(2026, 1, 1))


def test_common_plan_default_and_short_crop():
    sowing = date(2026, 10, 1)
    plan = build_common_plan(sowing)
    assert [t["week"] for t in plan][:6] == [1, 2, 3, 4, 5, 6]
    assert plan[5]["due_on"] == sowing
    assert plan[-1]["title_en"] == "Harvest"
    assert plan[-1]["due_on"] == sowing + timedelta(weeks=13)
    assert all(t["title_ta"] and t["body_ta"] for t in plan)
    short = build_common_plan(sowing, date(2026, 12, 20))
    assert short[-1]["due_on"] == date(2026, 12, 20)
    stop = next(t for t in short if t["title_en"] == "Stop sprays")
    assert stop["due_on"] == date(2026, 12, 6)
    assert all(t["due_on"] < stop["due_on"] for t in short if 6 < t["week"] < 17)


def test_forecast_is_fail_closed():
    assert forecast_gate([]) == "No farmers enrolled"
    assert forecast_gate([{"is_test": True}]) == "Insufficient data for harvest forecast"


@pytest.mark.asyncio
async def test_no_pilot_stays_unselected(db_session):
    user = User(firebase_uid="organic-empty-state", status="active")
    db_session.add(user)
    await db_session.flush()
    result = await setup_status(db_session, user)
    assert result["is_pilot_ready"] is False
    assert "FPO not selected" in result["statuses"]
    assert "Pilot crops not selected" in result["statuses"]


@pytest.mark.asyncio
async def test_plot_plan_and_partial_conversion_fail_closed(db_session):
    user = User(firebase_uid="organic-safe-farmer", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Real test farm")
    db_session.add(farm)
    await db_session.flush()
    plot = await add_plot(farm.id, PlotIn(name="South plot", area_hectares=0.5), db_session, user)
    assert plot["notice"] == TRIAL_NOTICE
    cycle = await add_crop_cycle(plot["id"], CropCycleIn(crop_id="rice", sowing_date=date(2026, 9, 16)), db_session, user)
    plan = await crop_plan(cycle["id"], db_session, user)
    assert plan["status"] == "ready"
    assert plan["source"] == COMMON_PLAN_VERSION
    assert plan["tasks"][0]["week"] == 1
    assert plan["notice_ta"] and plan["notice_en"]
    no_date = await add_crop_cycle(plot["id"], CropCycleIn(crop_id="rice"), db_session, user)
    assert (await crop_plan(no_date["id"], db_session, user))["status"] == "needs_sowing_date"
    assert (await pgs_status(farm.id, db_session, user))["notice"] == TRIAL_NOTICE
    result = await update_pgs_checklist(farm.id, PgsFarmerIn(partial_conversion=True), db_session, user)
    assert result["state"] == "regional_council_approval_required"
    audit = await db_session.scalar(select(AuditLog).where(
        AuditLog.action == "organic_pgs_checklist_updated",
        AuditLog.target_id == str(farm.id),
    ))
    assert audit is not None
    assert audit.meta["actor_user_id"] == str(user.id)
    assert audit.meta["prior_state"] == "pre_certification_trial"
    assert audit.meta["new_state"] == "regional_council_approval_required"
    assert audit.meta["occurred_at"]


@pytest.mark.asyncio
async def test_pgs_admin_transition_has_append_only_actor_record(db_session):
    farmer = User(firebase_uid="organic-audit-farmer", status="active")
    officer = User(firebase_uid="organic-audit-officer", status="active")
    db_session.add_all([farmer, officer])
    await db_session.flush()
    farm = Farm(user_id=farmer.id, name="Audit test farm")
    db_session.add(farm)
    await db_session.flush()
    await update_pgs_checklist(farm.id, PgsFarmerIn(), db_session, farmer)
    admin = AdminUser(user_id=officer.id, role=AdminRole.AGRICULTURE_OFFICER.value)
    db_session.add(admin)
    await db_session.flush()
    context = AdminContext(admin=admin, permissions=frozenset({AdminPermission.MANAGE_FARMERS.value}))
    result = await review_pgs(farm.id, PgsReviewIn(requested_state="pgs_eligibility_review"), db_session, context)
    assert result["state"] == "pgs_eligibility_review"
    audit = await db_session.scalar(select(AuditLog).where(AuditLog.action == "organic_pgs_state_reviewed"))
    assert audit is not None
    assert audit.admin_id == admin.id
    assert audit.meta["actor_user_id"] == str(officer.id)
    assert audit.meta["prior_state"] == "pre_certification_trial"
    assert audit.meta["new_state"] == "pgs_eligibility_review"
    assert audit.meta["occurred_at"]


@pytest.mark.asyncio
async def test_today_task_follows_common_plan(db_session):
    user = User(firebase_uid="organic-common-plan", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Common plan farm")
    db_session.add(farm)
    await db_session.flush()
    plot = await add_plot(farm.id, PlotIn(name="East plot"), db_session, user)
    await add_crop_cycle(plot["id"], CropCycleIn(crop_id="groundnut", sowing_date=date.today()), db_session, user)
    tasks = (await today_task(farm.id, db_session, user))["tasks"]
    assert [t["title_en"] for t in tasks] == ["Sow or transplant"]
    assert tasks[0]["week"] == 6


@pytest.mark.asyncio
async def test_saved_checklist_joins_officer_review_queue(db_session):
    farmer = User(firebase_uid="pgs-queue-farmer", status="active")
    officer = User(firebase_uid="pgs-queue-officer", status="active")
    db_session.add_all([farmer, officer])
    await db_session.flush()
    farm = Farm(user_id=farmer.id, name="Queue farm")
    db_session.add(farm)
    await db_session.flush()
    admin = AdminUser(user_id=officer.id, role=AdminRole.AGRICULTURE_OFFICER.value)
    db_session.add(admin)
    await db_session.flush()
    context = AdminContext(admin=admin, permissions=frozenset({AdminPermission.MANAGE_FARMERS.value}))

    # Nothing ticked: stays a trial and is not queued.
    result = await update_pgs_checklist(farm.id, PgsFarmerIn(), db_session, farmer)
    assert result["state"] == "pre_certification_trial"
    assert await admin_pgs_review_queue(db_session, context) == []

    # One item ticked: moves to eligibility review and appears in the officer queue.
    result = await update_pgs_checklist(
        farm.id, PgsFarmerIn(checklist={"whole_holding_reviewed": True}), db_session, farmer
    )
    assert result["state"] == "pgs_eligibility_review"
    queue = await admin_pgs_review_queue(db_session, context)
    assert [(row["farm_name"], row["items_ticked"]) for row in queue] == [("Queue farm", 1)]
