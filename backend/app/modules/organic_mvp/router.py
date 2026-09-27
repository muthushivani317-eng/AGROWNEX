"""Generic organic pilot workflows. Empty pilot state is intentional."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.admin.constants import AdminPermission, AdminRole
from app.modules.admin.dependencies import AdminContextDep
from app.modules.admin.models import AuditLog
from app.modules.auth.dependencies import CurrentUser
from app.modules.farms.models import Farm
from app.modules.notifications.models import FutureNotificationQueue
from app.modules.organic.models import OrganicCertificationDocument, OrganicFarmProfile
from app.modules.organic_mvp.common_plan import (
    COMMON_PLAN_VERSION,
    NOTICE_EN,
    NOTICE_TA,
    build_common_plan,
)
from app.modules.organic_mvp.engine import (
    READINESS_PATHWAYS,
    TRIAL_NOTICE,
    forecast_gate,
    schedule_reviewed_tasks,
    score_readiness,
    validate_pgs_transition,
)
from app.modules.organic_mvp.models import (
    OrganicCropCycle,
    OrganicFpo,
    OrganicPeerAppraisal,
    OrganicPgsCase,
    OrganicPilot,
    OrganicPilotEnrollment,
    OrganicPlot,
    OrganicReadiness,
    OrganicReadinessRules,
    OrganicScheduledTask,
    OrganicTaskTemplate,
)
from app.modules.organic_mvp.schemas import (
    AppraisalCompleteIn,
    AppraisalIn,
    CropCycleIn,
    EnrollIn,
    FpoIn,
    PgsFarmerIn,
    PgsReviewIn,
    PilotSetupIn,
    PlotIn,
    ReadinessAnswersIn,
    ReadinessRulesIn,
    ReviewIn,
    TemplateIn,
)

router = APIRouter(prefix="/organic-mvp", tags=["organic-mvp"])
admin_router = APIRouter(prefix="/admin/organic-mvp", tags=["organic-mvp-admin"])
Session = Annotated[AsyncSession, Depends(get_session)]


def _allow(admin, permission: AdminPermission):
    if permission.value not in admin.permissions:
        raise ForbiddenError("Organic pilot permission required.")


async def _farm(session: AsyncSession, farm_id: uuid.UUID, user_id: uuid.UUID) -> Farm:
    farm = await session.scalar(select(Farm).where(Farm.id == farm_id, Farm.user_id == user_id, Farm.deleted_at.is_(None)))
    if farm is None:
        raise NotFoundError("Farm not found.")
    return farm


async def _plot(session: AsyncSession, plot_id: uuid.UUID, user_id: uuid.UUID) -> OrganicPlot:
    plot = await session.get(OrganicPlot, plot_id)
    if plot is None:
        raise NotFoundError("Plot not found.")
    await _farm(session, plot.farm_id, user_id)
    return plot


def _pilot_status(pilot: OrganicPilot | None) -> list[str]:
    if pilot is None:
        return ["Pilot setup required", "FPO not selected", "Pilot crops not selected"]
    result = []
    if not pilot.district or not pilot.certification_pathway:
        result.append("Pilot setup required")
    if not pilot.fpo_id:
        result.append("FPO not selected")
    if not pilot.crop_ids:
        result.append("Pilot crops not selected")
    if not pilot.agronomist_user_id:
        result.append("Crop plan awaiting agronomist approval")
    return result


@router.get("/setup-status")
async def setup_status(session: Session, user: CurrentUser):
    pilot = await session.scalar(select(OrganicPilot).join(
        OrganicPilotEnrollment, OrganicPilotEnrollment.pilot_id == OrganicPilot.id).where(
        OrganicPilotEnrollment.farmer_user_id == user.id,
        OrganicPilotEnrollment.status == "enrolled",
        OrganicPilot.is_test.is_(False),
    ).order_by(OrganicPilot.created_at.desc()))
    any_pilot = await session.scalar(select(OrganicPilot.id).where(OrganicPilot.is_test.is_(False)).limit(1))
    statuses = _pilot_status(pilot) if pilot else (["Pilot setup required", "No farmers enrolled"] if any_pilot else _pilot_status(None))
    return {"pilot_id": str(pilot.id) if pilot else None, "statuses": statuses,
            "is_pilot_ready": bool(pilot and not statuses)}


@router.post("/farms/{farm_id}/plots")
async def add_plot(farm_id: uuid.UUID, body: PlotIn, session: Session, user: CurrentUser):
    await _farm(session, farm_id, user.id)
    plot = OrganicPlot(farm_id=farm_id, trial_only=True, **body.model_dump())
    session.add(plot)
    await session.commit()
    return {"id": str(plot.id), "notice": TRIAL_NOTICE if plot.trial_only else None}


@router.get("/farms/{farm_id}/plots")
async def list_plots(farm_id: uuid.UUID, session: Session, user: CurrentUser):
    await _farm(session, farm_id, user.id)
    plots = (await session.scalars(select(OrganicPlot).where(OrganicPlot.farm_id == farm_id))).all()
    return [{"id": str(row.id), "name": row.name, "area_hectares": row.area_hectares,
             "trial_only": row.trial_only, "notice": TRIAL_NOTICE if row.trial_only else None} for row in plots]


@router.post("/plots/{plot_id}/crop-cycles")
async def add_crop_cycle(plot_id: uuid.UUID, body: CropCycleIn, session: Session, user: CurrentUser):
    await _plot(session, plot_id, user.id)
    cycle = OrganicCropCycle(plot_id=plot_id, **body.model_dump())
    session.add(cycle)
    await session.commit()
    return {"id": str(cycle.id), "status": "ready" if cycle.sowing_date else "needs_sowing_date"}


@router.get("/plots/{plot_id}/crop-cycles")
async def list_crop_cycles(plot_id: uuid.UUID, session: Session, user: CurrentUser):
    await _plot(session, plot_id, user.id)
    cycles = (await session.scalars(select(OrganicCropCycle).where(OrganicCropCycle.plot_id == plot_id))).all()
    return [{"id": str(row.id), "crop_id": row.crop_id, "sowing_date": row.sowing_date,
             "expected_harvest_start": row.expected_harvest_start,
             "expected_harvest_end": row.expected_harvest_end,
             "expected_quantity_kg": row.expected_quantity_kg} for row in cycles]


@router.get("/readiness/questions")
async def readiness_questions(session: Session, user: CurrentUser):
    rules = await session.scalar(
        select(OrganicReadinessRules)
        .where(OrganicReadinessRules.status == "approved")
        .order_by(OrganicReadinessRules.approved_at.desc())
    )
    return {"status": "ready" if rules else "Pilot setup required", "version": rules.version if rules else None,
            "questions": rules.questions if rules else []}


@router.post("/farms/{farm_id}/readiness")
async def assess_readiness(farm_id: uuid.UUID, body: ReadinessAnswersIn, session: Session, user: CurrentUser):
    await _farm(session, farm_id, user.id)
    rules = await session.scalar(
        select(OrganicReadinessRules)
        .where(OrganicReadinessRules.status == "approved")
        .order_by(OrganicReadinessRules.approved_at.desc())
    )
    if rules is None:
        raise ConflictError("Readiness questions await expert review.")
    result = score_readiness(body.answers, {"questions": rules.questions, **rules.scoring})
    row = OrganicReadiness(farm_id=farm_id, farmer_user_id=user.id, answers=body.answers,
                           rules_version=rules.version, score=result["score"], pathway=result["pathway"],
                           risk_flags=result["risk_flags"])
    session.add(row)
    await session.commit()
    return {"id": str(row.id), **result, "certification_notice": TRIAL_NOTICE}


@router.get("/farms/{farm_id}/readiness")
async def readiness_history(farm_id: uuid.UUID, session: Session, user: CurrentUser):
    await _farm(session, farm_id, user.id)
    rows = (await session.scalars(select(OrganicReadiness).where(OrganicReadiness.farm_id == farm_id).order_by(OrganicReadiness.created_at.desc()))).all()
    return [{"id": str(row.id), "score": row.score, "pathway": row.pathway,
             "rules_version": row.rules_version, "risk_flags": row.risk_flags} for row in rows]


PGS_REVIEW_QUEUE_STATES = ("pgs_eligibility_review", "regional_council_approval_required", "non_compliance_review")


@router.get("/farms/{farm_id}/pgs")
async def pgs_status(farm_id: uuid.UUID, session: Session, user: CurrentUser):
    await _farm(session, farm_id, user.id)
    row = await session.scalar(select(OrganicPgsCase).where(OrganicPgsCase.farm_id == farm_id))
    if row is None:
        return {"state": "pre_certification_trial", "notice": TRIAL_NOTICE, "checklist": {}, "appraisals": []}
    appraisals = (await session.scalars(select(OrganicPeerAppraisal).where(OrganicPeerAppraisal.case_id == row.id))).all()
    effective_state = row.state
    if effective_state in {"pgs_green_under_conversion", "pgs_organic"} and (not row.valid_to or row.valid_to < date.today()):
        effective_state = "pgs_eligibility_review"
    return {"state": effective_state, "notice": TRIAL_NOTICE if effective_state == "pre_certification_trial" else None,
            "partial_conversion": row.partial_conversion, "checklist": row.checklist,
            "certificate_id": row.certificate_id if row.verified_at else None,
            "issuing_authority": row.issuing_authority if row.verified_at else None,
            "valid_to": row.valid_to if row.verified_at else None,
            "appraisals": [{"id": str(a.id), "scheduled_on": a.scheduled_on, "status": a.status} for a in appraisals]}


@router.put("/farms/{farm_id}/pgs/checklist")
async def update_pgs_checklist(farm_id: uuid.UUID, body: PgsFarmerIn, session: Session, user: CurrentUser):
    await _farm(session, farm_id, user.id)
    row = await session.scalar(select(OrganicPgsCase).where(OrganicPgsCase.farm_id == farm_id))
    if row is None:
        row = OrganicPgsCase(farm_id=farm_id, farmer_user_id=user.id)
        session.add(row)
    prior_state = row.state or "pre_certification_trial"
    prior_partial_conversion = bool(row.partial_conversion)
    prior_checklist = dict(row.checklist or {})
    row.checklist = body.checklist
    row.partial_conversion = body.partial_conversion
    if body.partial_conversion and not row.regional_council_approval_ref:
        row.state = "regional_council_approval_required"
    elif prior_state == "pre_certification_trial" and any(body.checklist.values()):
        # A saved checklist with at least one item ticked is a request for review:
        # it joins the agriculture officer's review queue. Only an officer can
        # move it further; the farmer never grants a certified status.
        row.state = "pgs_eligibility_review"
    elif row.state in {"pgs_green_under_conversion", "pgs_organic"}:
        # A farmer cannot retain a verified label after changing conversion evidence.
        row.state = "pgs_eligibility_review"
        row.verified_by = None
        row.verified_at = None
    session.add(AuditLog(
        role="farmer", action="organic_pgs_checklist_updated",
        target="organic_pgs_case", target_id=str(farm_id),
        meta={"actor_user_id": str(user.id), "prior_state": prior_state,
              "new_state": row.state, "prior_partial_conversion": prior_partial_conversion,
              "new_partial_conversion": row.partial_conversion,
              "prior_checklist": prior_checklist, "new_checklist": dict(row.checklist or {}),
              "occurred_at": datetime.now(UTC).isoformat()},
    ))
    await session.commit()
    return {"state": row.state, "notice": TRIAL_NOTICE if row.state == "pre_certification_trial" else None}


@router.get("/crop-cycles/{cycle_id}/plan")
async def crop_plan(cycle_id: uuid.UUID, session: Session, user: CurrentUser):
    cycle = await session.get(OrganicCropCycle, cycle_id)
    if cycle is None:
        raise NotFoundError("Crop cycle not found.")
    await _plot(session, cycle.plot_id, user.id)
    tasks = (
        await session.scalars(
            select(OrganicScheduledTask)
            .where(OrganicScheduledTask.crop_cycle_id == cycle_id)
            .order_by(OrganicScheduledTask.due_on)
        )
    ).all()
    if tasks:
        return {"status": "ready", "source": "reviewed_template",
                "notice_ta": NOTICE_TA, "notice_en": NOTICE_EN,
                "tasks": [{"id": str(t.id), "week": None, "due_on": t.due_on, "title_ta": t.title_ta,
                           "body_ta": t.body_ta, "title_en": t.title_en, "body_en": t.body_en,
                           "status": t.status} for t in tasks]}
    # No crop-specific plan activated: fall back to the KVK-approved common plan.
    if not cycle.sowing_date:
        return {"status": "needs_sowing_date", "source": COMMON_PLAN_VERSION,
                "notice_ta": NOTICE_TA, "notice_en": NOTICE_EN, "tasks": []}
    return {"status": "ready", "source": COMMON_PLAN_VERSION,
            "notice_ta": NOTICE_TA, "notice_en": NOTICE_EN,
            "tasks": [_common_task_out(cycle.id, t) for t in
                      build_common_plan(cycle.sowing_date, cycle.expected_harvest_start)]}


def _common_task_out(cycle_id: uuid.UUID, task: dict, **extra) -> dict:
    return {"id": f"common:{cycle_id}:{task['week']}", "week": task["week"],
            "due_on": task["due_on"], "title_ta": task["title_ta"], "body_ta": task["body_ta"],
            "title_en": task["title_en"], "body_en": task["body_en"], "status": "pending", **extra}


@router.get("/farms/{farm_id}/today-task")
async def today_task(farm_id: uuid.UUID, session: Session, user: CurrentUser):
    """Today's due organic task(s) for a farm -- across all activated crop-cycle
    plans, not just one cycle. Surfaces overdue-but-unresolved tasks too (never
    hides a pending task just because its due date passed), same "don't hide
    unresolved work" principle as daily_task's own cooldown logic. Read-only;
    marking a task done happens via the logbook, not here (no PATCH at MVP).
    """
    await _farm(session, farm_id, user.id)
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    rows = (
        await session.scalars(
            select(OrganicScheduledTask)
            .join(OrganicCropCycle, OrganicCropCycle.id == OrganicScheduledTask.crop_cycle_id)
            .join(OrganicPlot, OrganicPlot.id == OrganicCropCycle.plot_id)
            .where(
                OrganicPlot.farm_id == farm_id,
                OrganicScheduledTask.status == "pending",
                OrganicScheduledTask.due_on <= today,
            )
            .order_by(OrganicScheduledTask.due_on)
            .limit(3)
        )
    ).all()
    result = [{"id": str(t.id), "due_on": t.due_on, "title_ta": t.title_ta,
               "body_ta": t.body_ta, "title_en": t.title_en, "body_en": t.body_en,
               "is_overdue": t.due_on < today} for t in rows]
    # Crop cycles without an activated crop-specific plan follow the common plan:
    # show the step whose week is running now (due within the last 7 days).
    cycles = (
        await session.scalars(
            select(OrganicCropCycle)
            .join(OrganicPlot, OrganicPlot.id == OrganicCropCycle.plot_id)
            .where(OrganicPlot.farm_id == farm_id, OrganicCropCycle.sowing_date.is_not(None))
        )
    ).all()
    for cycle in cycles:
        has_reviewed = await session.scalar(select(OrganicScheduledTask.id).where(
            OrganicScheduledTask.crop_cycle_id == cycle.id).limit(1))
        if has_reviewed:
            continue
        for task in build_common_plan(cycle.sowing_date, cycle.expected_harvest_start):
            if task["due_on"] <= today < task["due_on"] + timedelta(days=7):
                item = _common_task_out(cycle.id, task, is_overdue=False)
                item.pop("status")
                result.append(item)
    result.sort(key=lambda item: item["due_on"])
    return {"tasks": result[:3]}


@admin_router.post("/pilot")
async def setup_pilot(body: PilotSetupIn, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_FARMERS)
    fpo = await session.get(OrganicFpo, body.fpo_id) if body.fpo_id else None
    if body.fpo_id and (fpo is None or fpo.is_test != body.is_test):
        raise ValidationError("Selected FPO does not exist in this data environment.")
    if fpo and body.district and fpo.district != body.district:
        raise ValidationError("Pilot district must match the selected FPO.")
    values = body.model_dump()
    values["fpo_name"] = fpo.name if fpo else None
    values["district"] = fpo.district if fpo else body.district
    pilot = OrganicPilot(
        **values,
        status="setup_required"
        if not (
            fpo
            and values["district"]
            and body.crop_ids
            and body.agronomist_user_id
            and body.certification_pathway
        )
        else "configured",
    )
    session.add(pilot)
    await session.commit()
    return {"id": str(pilot.id), "statuses": _pilot_status(pilot)}


@admin_router.post("/fpos")
async def create_fpo(body: FpoIn, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_FARMERS)
    row = OrganicFpo(**body.model_dump())
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "name": row.name, "district": row.district, "is_test": row.is_test}


@admin_router.get("/fpos")
async def list_fpos(session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.VIEW_DASHBOARD)
    rows = (await session.scalars(select(OrganicFpo).order_by(OrganicFpo.created_at.desc()))).all()
    return [{"id": str(row.id), "name": row.name, "district": row.district,
             "registration_reference": row.registration_reference, "is_test": row.is_test} for row in rows]


@admin_router.get("/pilots")
async def list_pilots(session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.VIEW_DASHBOARD)
    pilots = (await session.scalars(select(OrganicPilot).order_by(OrganicPilot.created_at.desc()))).all()
    return [{"id": str(p.id), "fpo_id": str(p.fpo_id) if p.fpo_id else None,
             "fpo_name": p.fpo_name, "district": p.district,
             "crop_ids": p.crop_ids, "agronomist_user_id": str(p.agronomist_user_id) if p.agronomist_user_id else None,
             "certification_pathway": p.certification_pathway, "is_test": p.is_test,
             "statuses": _pilot_status(p)} for p in pilots]


@admin_router.put("/pilot/{pilot_id}")
async def update_pilot(pilot_id: uuid.UUID, body: PilotSetupIn, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_FARMERS)
    pilot = await session.get(OrganicPilot, pilot_id)
    if pilot is None:
        raise NotFoundError("Pilot not found.")
    if pilot.is_test != body.is_test:
        raise ValidationError("A test pilot cannot be converted into production data.")
    fpo = await session.get(OrganicFpo, body.fpo_id) if body.fpo_id else None
    if body.fpo_id and (fpo is None or fpo.is_test != pilot.is_test):
        raise ValidationError("Selected FPO does not exist in this data environment.")
    if fpo and body.district and fpo.district != body.district:
        raise ValidationError("Pilot district must match the selected FPO.")
    values = body.model_dump()
    values["fpo_name"] = fpo.name if fpo else None
    values["district"] = fpo.district if fpo else body.district
    for key, value in values.items():
        setattr(pilot, key, value)
    pilot.status = (
        "configured"
        if (
            pilot.fpo_id
            and pilot.district
            and pilot.crop_ids
            and pilot.agronomist_user_id
            and pilot.certification_pathway
        )
        else "setup_required"
    )
    await session.commit()
    return {"id": str(pilot.id), "statuses": _pilot_status(pilot)}


@admin_router.get("/pilot/{pilot_id}")
async def pilot_detail(pilot_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.VIEW_DASHBOARD)
    pilot = await session.get(OrganicPilot, pilot_id)
    if pilot is None:
        raise NotFoundError("Pilot not found.")
    return {"id": str(pilot.id), "fpo_id": str(pilot.fpo_id) if pilot.fpo_id else None,
            "fpo_name": pilot.fpo_name, "district": pilot.district,
            "crop_ids": pilot.crop_ids, "agronomist_user_id": pilot.agronomist_user_id,
            "certification_pathway": pilot.certification_pathway, "is_test": pilot.is_test,
            "statuses": _pilot_status(pilot)}


@admin_router.post("/pilot/{pilot_id}/enroll")
async def enroll(pilot_id: uuid.UUID, body: EnrollIn, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_FARMERS)
    pilot = await session.get(OrganicPilot, pilot_id)
    if pilot is None:
        raise NotFoundError("Pilot not found.")
    farm = await _farm(session, body.farm_id, body.farmer_user_id)
    if not body.consent_confirmed:
        raise ValidationError("Farmer consent is required.")
    existing = await session.scalar(
        select(OrganicPilotEnrollment).where(
            OrganicPilotEnrollment.pilot_id == pilot_id,
            OrganicPilotEnrollment.farm_id == farm.id,
        )
    )
    if existing:
        raise ConflictError("Farm is already enrolled.")
    row = OrganicPilotEnrollment(pilot_id=pilot_id, farm_id=farm.id, farmer_user_id=body.farmer_user_id,
                                  consent_at=datetime.now(UTC))
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "status": row.status}


@admin_router.post("/readiness-rules")
async def create_rules(body: ReadinessRulesIn, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_CONTENT)
    # Validate the complete scoring contract before any farmer can see it.
    for q in body.questions:
        if not q.get("id") or not isinstance(q.get("options"), dict) or not q["options"]:
            raise ValidationError("Each question needs an ID and answer options.")
        if not q.get("title_ta"):
            raise ValidationError("Each question needs Tamil text.")
        for choice in q["options"].values():
            if not isinstance(choice.get("points"), int) or choice["points"] < 0:
                raise ValidationError("Every answer needs nonnegative points.")
    if not body.scoring.get("bands"):
        raise ValidationError("Scoring bands are required.")
    for band in body.scoring["bands"]:
        if (not isinstance(band, dict) or band.get("pathway") not in READINESS_PATHWAYS
            or not band.get("recommendation_ta")
            or not isinstance(band.get("min"), int)
            or not isinstance(band.get("max"), int)
            or not 0 <= band["min"] <= band["max"] <= 100):
            raise ValidationError("Readiness bands must be complete, bounded and non-certifying.")
    row = OrganicReadinessRules(**body.model_dump(), status="draft")
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "status": row.status}


@admin_router.get("/readiness-rules")
async def list_rules(session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_CONTENT)
    rows = (await session.scalars(select(OrganicReadinessRules).order_by(OrganicReadinessRules.created_at.desc()))).all()
    return [{"id": str(row.id), "version": row.version, "questions": row.questions,
             "scoring": row.scoring, "status": row.status} for row in rows]


@admin_router.post("/readiness-rules/{rule_id}/review")
async def review_rules(rule_id: uuid.UUID, body: ReviewIn, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_CONTENT)
    row = await session.get(OrganicReadinessRules, rule_id)
    if row is None:
        raise NotFoundError("Rules not found.")
    row.status = "approved" if body.approved else "rejected"
    row.approved_by = admin.admin.user_id if body.approved else None
    row.approved_at = datetime.now(UTC) if body.approved else None
    await session.commit()
    return {"status": row.status}


@admin_router.post("/task-templates")
async def create_template(body: TemplateIn, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_CONTENT)
    if body.tasks:
        schedule_reviewed_tasks(body.tasks, date.today())  # structure validation only
    row = OrganicTaskTemplate(**body.model_dump(), status="draft")
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "status": row.status}


@admin_router.get("/task-templates")
async def list_templates(session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_CONTENT)
    rows = (await session.scalars(select(OrganicTaskTemplate).order_by(OrganicTaskTemplate.created_at.desc()))).all()
    return [{"id": str(row.id), "crop_id": row.crop_id, "district": row.district,
             "version": row.version, "tasks": row.tasks, "status": row.status,
             "agronomist_user_id": str(row.agronomist_user_id) if row.agronomist_user_id else None}
            for row in rows]


@admin_router.post("/task-templates/{template_id}/review")
async def review_template(template_id: uuid.UUID, body: ReviewIn, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_CONTENT)
    if admin.admin.role not in {AdminRole.AGRICULTURE_OFFICER.value, AdminRole.OWNER.value, AdminRole.SUPER_ADMIN.value}:
        raise ForbiddenError("Agronomist review role required.")
    row = await session.get(OrganicTaskTemplate, template_id)
    if row is None:
        raise NotFoundError("Template not found.")
    pilot = await session.scalar(select(OrganicPilot).where(
        OrganicPilot.district == row.district,
        OrganicPilot.agronomist_user_id == admin.admin.user_id,
    ))
    if body.approved and (pilot is None or row.crop_id not in pilot.crop_ids):
        raise ForbiddenError("The assigned pilot agronomist must review this crop plan.")
    if body.approved and not row.tasks:
        raise ValidationError("An empty crop plan cannot be approved.")
    row.status = "agronomist_reviewed" if body.approved else "rejected"
    row.agronomist_user_id = admin.admin.user_id if body.approved else None
    row.reviewed_at = datetime.now(UTC) if body.approved else None
    row.review_note = body.note
    await session.commit()
    return {"status": row.status}


@admin_router.post("/crop-cycles/{cycle_id}/activate-plan")
async def activate_plan(cycle_id: uuid.UUID, template_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_CONTENT)
    cycle = await session.get(OrganicCropCycle, cycle_id)
    template = await session.get(OrganicTaskTemplate, template_id)
    if cycle is None or template is None:
        raise NotFoundError("Crop cycle or template not found.")
    if template.status != "agronomist_reviewed" or not template.agronomist_user_id:
        raise ConflictError("Crop plan awaiting agronomist approval.")
    if cycle.crop_id != template.crop_id:
        raise ValidationError("Template crop does not match crop cycle.")
    tasks = schedule_reviewed_tasks(template.tasks, cycle.sowing_date)
    if await session.scalar(select(OrganicScheduledTask.id).where(OrganicScheduledTask.crop_cycle_id == cycle_id).limit(1)):
        raise ConflictError("Crop plan already activated.")
    plot = await session.get(OrganicPlot, cycle.plot_id)
    farm = await session.get(Farm, plot.farm_id) if plot else None
    if farm is None:
        raise NotFoundError("Farm not found.")
    enrollment = await session.scalar(select(OrganicPilotEnrollment).join(
        OrganicPilot, OrganicPilot.id == OrganicPilotEnrollment.pilot_id).where(
        OrganicPilotEnrollment.farm_id == farm.id,
        OrganicPilotEnrollment.status == "enrolled",
        OrganicPilot.is_test.is_(False),
        OrganicPilot.district == template.district,
    ))
    if enrollment is None:
        raise ConflictError("Pilot setup and real farmer enrollment are required before activation.")
    for index, task in enumerate(tasks):
        session.add(OrganicScheduledTask(crop_cycle_id=cycle_id, template_id=template_id,
                  day_offset=task["day_offset"], due_on=task["due_on"],
                  title_ta=task["title_ta"], body_ta=task["body_ta"],
                  title_en=task.get("title_en"), body_en=task.get("body_en")))
        reminder_at = datetime.combine(task["due_on"], time(6, 0), tzinfo=ZoneInfo("Asia/Kolkata")).astimezone(UTC)
        if reminder_at > datetime.now(UTC):
            session.add(FutureNotificationQueue(
                user_id=farm.user_id, farm_id=farm.id, module="calendar", event_type="organic_task_due",
                title_key="organic.mvpTaskReminderTitle", message_key="organic.mvpTaskReminderBody",
                payload_json={"crop": cycle.crop_id}, severity="info", priority="medium",
                action_route=f"/organic/conversion-plan?farmId={farm.id}",
                dedup_key=f"organic-plan:{cycle_id}:{template_id}:{index}",
                scheduled_for=reminder_at, expires_at=reminder_at + timedelta(days=2), processed=False))
    await session.commit()
    return {"status": "active", "task_count": len(tasks)}


@admin_router.post("/farms/{farm_id}/pgs/review")
async def review_pgs(farm_id: uuid.UUID, body: PgsReviewIn, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_FARMERS)
    if admin.admin.role not in {AdminRole.AGRICULTURE_OFFICER.value, AdminRole.OWNER.value, AdminRole.SUPER_ADMIN.value}:
        raise ForbiddenError("PGS evidence review requires an agriculture-officer role.")
    row = await session.scalar(select(OrganicPgsCase).where(OrganicPgsCase.farm_id == farm_id))
    if row is None:
        raise NotFoundError("PGS case not found.")
    if body.requested_state in {"pgs_green_under_conversion", "pgs_organic"}:
        if body.certificate_document_id is None:
            raise ValidationError("Certificate evidence document is required.")
        document = await session.get(OrganicCertificationDocument, body.certificate_document_id)
        profile = await session.scalar(select(OrganicFarmProfile).where(OrganicFarmProfile.farm_id == farm_id))
        if document is None or profile is None or document.profile_id != profile.id:
            raise ValidationError("Certificate evidence must belong to this farm.")
        if document.review_status != "approved":
            raise ValidationError("Certificate document has not been verified.")
    if body.requested_state == "pgs_organic" and not (
        row.checklist.get("whole_holding_reviewed") is True
        and row.checklist.get("conversion_plan_recorded") is True
        and row.checklist.get("conversion_completed") is True
        and row.checklist.get("no_major_non_compliance") is True
    ):
        raise ValidationError("Completed conversion and no major non-compliance must be checked.")
    validate_pgs_transition(requested=body.requested_state,
        partial_conversion=row.partial_conversion,
        council_approval_ref=body.regional_council_approval_ref or row.regional_council_approval_ref,
        certificate_id=body.certificate_id, issuing_authority=body.issuing_authority,
        valid_from=body.valid_from, valid_to=body.valid_to,
        verified=body.verified_evidence, major_non_compliance=body.major_non_compliance)
    prior_state = row.state
    row.state = body.requested_state
    row.regional_council_approval_ref = body.regional_council_approval_ref or row.regional_council_approval_ref
    row.certificate_id = body.certificate_id
    row.certificate_document_id = body.certificate_document_id
    row.issuing_authority = body.issuing_authority
    row.valid_from, row.valid_to = body.valid_from, body.valid_to
    row.verified_by = admin.admin.user_id if body.verified_evidence else None
    row.verified_at = datetime.now(UTC) if body.verified_evidence else None
    row.non_compliance_note = body.non_compliance_note
    session.add(AuditLog(
        admin_id=admin.admin.id, role=admin.admin.role,
        action="organic_pgs_state_reviewed", target="organic_pgs_case",
        target_id=str(row.id), ip_address=admin.ip_address,
        meta={"actor_user_id": str(admin.admin.user_id),
              "prior_state": prior_state, "new_state": row.state,
              "certificate_document_id": str(body.certificate_document_id) if body.certificate_document_id else None,
              "verified_evidence": body.verified_evidence,
              "occurred_at": datetime.now(UTC).isoformat()},
    ))
    await session.commit()
    return {"state": row.state}


@admin_router.get("/pgs/review-queue")
async def admin_pgs_review_queue(session: Session, admin: AdminContextDep):
    """PGS cases waiting for an agriculture officer, oldest update first."""
    _allow(admin, AdminPermission.MANAGE_FARMERS)
    rows = (await session.execute(
        select(OrganicPgsCase, Farm.name)
        .join(Farm, Farm.id == OrganicPgsCase.farm_id)
        .where(OrganicPgsCase.state.in_(PGS_REVIEW_QUEUE_STATES))
        .order_by(OrganicPgsCase.updated_at)
        .limit(200)
    )).all()
    return [{"farm_id": str(case.farm_id), "farm_name": name, "state": case.state,
             "partial_conversion": case.partial_conversion,
             "items_ticked": sum(1 for value in (case.checklist or {}).values() if value),
             "updated_at": case.updated_at} for case, name in rows]


@admin_router.get("/farms/{farm_id}/pgs")
async def admin_pgs_case(farm_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_FARMERS)
    row = await session.scalar(select(OrganicPgsCase).where(OrganicPgsCase.farm_id == farm_id))
    if row is None:
        return {"status": "No PGS case", "state": "pre_certification_trial", "notice": TRIAL_NOTICE}
    profile = await session.scalar(select(OrganicFarmProfile).where(OrganicFarmProfile.farm_id == farm_id))
    documents = (await session.scalars(select(OrganicCertificationDocument).where(
        OrganicCertificationDocument.profile_id == profile.id))).all() if profile else []
    return {"id": str(row.id), "state": row.state, "partial_conversion": row.partial_conversion,
            "checklist": row.checklist, "regional_council_approval_ref": row.regional_council_approval_ref,
            "certificate_id": row.certificate_id, "issuing_authority": row.issuing_authority,
            "valid_from": row.valid_from, "valid_to": row.valid_to,
            "documents": [{"id": str(doc.id), "file_name": doc.file_name, "review_status": doc.review_status} for doc in documents]}


@admin_router.post("/farms/{farm_id}/pgs/appraisals")
async def schedule_appraisal(farm_id: uuid.UUID, body: AppraisalIn, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.MANAGE_FARMERS)
    case = await session.scalar(select(OrganicPgsCase).where(OrganicPgsCase.farm_id == farm_id))
    if case is None:
        raise NotFoundError("PGS case not found.")
    appraisal = OrganicPeerAppraisal(case_id=case.id, **body.model_dump())
    session.add(appraisal)
    await session.commit()
    return {"id": str(appraisal.id), "status": appraisal.status}


@router.get("/pgs/peer-assignments")
async def peer_assignments(session: Session, user: CurrentUser):
    rows = (await session.scalars(select(OrganicPeerAppraisal).where(
        OrganicPeerAppraisal.peer_user_id == user.id).order_by(OrganicPeerAppraisal.scheduled_on.desc()))).all()
    result = []
    for row in rows:
        case = await session.get(OrganicPgsCase, row.case_id)
        farm = await session.get(Farm, case.farm_id) if case else None
        result.append({"id": str(row.id), "case_id": str(row.case_id),
                       "farm_id": str(farm.id) if farm else None,
                       "farm_name": farm.name if farm else None,
                       "scheduled_on": row.scheduled_on, "status": row.status})
    return result


@router.post("/pgs/peer-assignments/{appraisal_id}/submit")
async def complete_appraisal(appraisal_id: uuid.UUID, body: AppraisalCompleteIn, session: Session, user: CurrentUser):
    row = await session.get(OrganicPeerAppraisal, appraisal_id)
    if row is None or row.peer_user_id != user.id:
        raise NotFoundError("Appraisal not found.")
    if row.status != "scheduled":
        raise ConflictError("Appraisal has already been submitted.")
    if not body.findings:
        raise ValidationError("Peer findings are required.")
    row.findings = body.findings
    row.status = "completed"
    row.completed_at = datetime.now(UTC)
    await session.commit()
    return {"status": row.status}


@admin_router.get("/pilot/{pilot_id}/harvest-dashboard")
async def harvest_dashboard(pilot_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _allow(admin, AdminPermission.VIEW_DASHBOARD)
    pilot = await session.get(OrganicPilot, pilot_id)
    if pilot is None:
        raise NotFoundError("Pilot not found.")
    statuses = _pilot_status(pilot)
    enrolled = (
        await session.scalars(
            select(OrganicPilotEnrollment).where(
                OrganicPilotEnrollment.pilot_id == pilot_id,
                OrganicPilotEnrollment.status == "enrolled",
            )
        )
    ).all()
    rows = []
    for enrollment in enrolled:
        plots = (await session.scalars(select(OrganicPlot).where(OrganicPlot.farm_id == enrollment.farm_id))).all()
        for plot in plots:
            cycles = (await session.scalars(select(OrganicCropCycle).where(OrganicCropCycle.plot_id == plot.id))).all()
            for cycle in cycles:
                if pilot.crop_ids and cycle.crop_id not in pilot.crop_ids:
                    continue
                rows.append({"farm_id": str(enrollment.farm_id), "plot_id": str(plot.id), "area_hectares": plot.area_hectares,
                             "crop_id": cycle.crop_id, "sowing_date": cycle.sowing_date,
                             "expected_harvest_start": cycle.expected_harvest_start,
                             "expected_harvest_end": cycle.expected_harvest_end,
                             "expected_quantity_kg": cycle.expected_quantity_kg,
                             "is_test": pilot.is_test})
    gate = "Insufficient data for harvest forecast" if enrolled and not rows else forecast_gate(rows)
    if not enrolled:
        statuses.append("No farmers enrolled")
    elif gate:
        statuses.append(gate)
    statuses.append("Buyer demand not yet verified")
    ready = not gate and not _pilot_status(pilot)
    forecast = None
    if ready and all(row["expected_quantity_kg"] is not None for row in rows):
        forecast = {crop: {"farmer_entered_expected_kg": sum(
            row["expected_quantity_kg"] for row in rows if row["crop_id"] == crop),
            "source": "farmer_entered_not_verified"}
            for crop in set(row["crop_id"] for row in rows)}
    elif ready:
        statuses.append("Insufficient data for harvest forecast")
    return {"pilot_id": str(pilot.id), "is_test": pilot.is_test,
            "enrolled_farm_count": len(enrolled), "statuses": statuses,
            "acreage_by_crop": {} if not ready else {
                crop: sum(area for area in {
                    r["plot_id"]: r["area_hectares"] for r in rows if r["crop_id"] == crop
                }.values()) for crop in set(r["crop_id"] for r in rows)},
            "forecast": forecast, "buyer_prices": None}
