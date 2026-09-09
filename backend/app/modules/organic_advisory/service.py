from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_verification.models import ActionWorkflow
from app.modules.action_verification.schemas import ActionOut
from app.modules.action_verification.service import ActionVerificationService
from app.modules.action_verification.source_adapter import SourceAction
from app.modules.auth.models import User
from app.modules.organic.repositories import OrganicRepository
from app.modules.satellite.constants import CLOUD_USABLE_MAX, SessionStatus
from app.modules.satellite.models import SatelliteAlert, SatelliteSession

from .exceptions import OrganicAdvisoryNotAllowedError, OrganicAdvisoryReferenceError
from .schemas import (
    SatelliteScoutingIn,
    SatelliteScoutingOut,
    WeatherOrganicGateIn,
    WeatherOrganicGateOut,
)

_WEATHER_GATE_ACTIONS = {
    "spraying.avoid_rain": "postpone_organic_application_for_rain",
    "spraying.avoid_wind": "postpone_organic_application_for_wind",
    "heavy_rain.expected": "postpone_organic_application_for_heavy_rain",
    "heavy_rain.severe": "postpone_organic_application_for_heavy_rain",
}
_SCOUTING_CHECKLISTS = {
    "vegetation": [
        "inspect_crop_vigor_pattern", "look_for_visible_pest_or_disease_symptoms",
        "look_for_visible_nutrient_symptoms", "record_photos_and_field_notes",
    ],
    "moisture": [
        "inspect_soil_moisture", "check_irrigation_and_drainage",
        "check_mulch_coverage", "record_photos_and_field_notes",
    ],
    "variation": [
        "inspect_flagged_field_zones", "check_weed_pressure",
        "check_moisture_and_mulch_uniformity", "check_amendment_distribution",
        "record_photos_and_field_notes",
    ],
    "seasonal": [
        "confirm_crop_stage", "inspect_physical_crop_condition",
        "record_photos_and_field_notes",
    ],
}


class OrganicAdvisoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.actions = ActionVerificationService(session)
        self.organic = OrganicRepository(session)

    async def weather_gate(
        self, user: User, payload: WeatherOrganicGateIn
    ) -> WeatherOrganicGateOut:
        original = await self.session.get(ActionWorkflow, payload.action_workflow_id)
        if (
            original is None or original.is_deleted or original.user_id != user.id
            or original.farm_id != payload.farm_id
        ):
            raise OrganicAdvisoryReferenceError()
        if not original.source_module.startswith("organic_") or original.status not in {
            "suggested", "viewed", "deferred"
        }:
            raise OrganicAdvisoryNotAllowedError()
        item = await self.organic.approved_input(payload.organic_input_id, date.today())
        if item is None:
            raise OrganicAdvisoryReferenceError()

        # The catalogue must explicitly allow this gate. Weather alone never
        # creates agronomy. Supported entries use limitations.weather_gates.
        allowed = {
            str(code) for code in (item.limitations or {}).get("weather_gates", [])
        }
        if payload.signal_code not in allowed:
            raise OrganicAdvisoryNotAllowedError()
        now = datetime.now(UTC)
        if payload.forecast_valid_until.astimezone(UTC) <= now:
            raise OrganicAdvisoryNotAllowedError()

        source = SourceAction(
            source_feature="organic_weather_gate",
            source_record_id=(
                f"{original.id}:{payload.signal_code}:"
                f"{payload.forecast_observed_at.astimezone(UTC).isoformat()}"
            ),
            source_version=f"{item.source_version}|{payload.forecast_version}",
            action_code=_WEATHER_GATE_ACTIONS[payload.signal_code],
            suggestion_time=now,
            due_at=payload.safe_after,
            expires_at=payload.forecast_valid_until,
            crop_cycle_id=original.crop_cycle_id,
            # Catalogue guidance is approved, but forecast fields currently
            # arrive through a farmer API and are not independently attested.
            source_verified=False,
        )
        gate = await self.actions.register_source_action(user, payload.farm_id, source)
        if gate is None:  # Defensive: validated inputs above should be actionable.
            raise OrganicAdvisoryNotAllowedError()
        return WeatherOrganicGateOut(
            original_action_id=original.id,
            gate_action=ActionOut.from_row(gate),
            explanation=(
                "Postponement only: the weather signal gates an approved organic "
                "action and does not create a new treatment recommendation."
            ),
        )

    async def satellite_scouting(
        self, user: User, payload: SatelliteScoutingIn
    ) -> SatelliteScoutingOut:
        alert = await self.session.get(SatelliteAlert, payload.satellite_alert_id)
        if (
            alert is None or alert.user_id != user.id or alert.farm_id != payload.farm_id
        ):
            raise OrganicAdvisoryReferenceError()
        session = await self.session.get(SatelliteSession, alert.session_id)
        if (
            session is None or session.user_id != user.id or session.farm_id != payload.farm_id
            or session.is_deleted or session.status != SessionStatus.AVAILABLE.value
            or session.is_sample or session.capture_date is None
            or session.cloud_cover is None or session.cloud_cover > CLOUD_USABLE_MAX
        ):
            raise OrganicAdvisoryNotAllowedError()
        checklist = _SCOUTING_CHECKLISTS.get(alert.category)
        if checklist is None:
            # Imagery-availability alerts must never become field diagnoses/tasks.
            raise OrganicAdvisoryNotAllowedError()
        now = datetime.now(UTC)
        if (
            payload.expires_at.astimezone(UTC) <= now
            or payload.expires_at.astimezone(UTC) > now + timedelta(days=7)
        ):
            raise OrganicAdvisoryNotAllowedError()
        scene_id = str((session.session_metadata or {}).get("scene_id") or session.id)
        source = SourceAction(
            source_feature="satellite_field_scouting",
            source_record_id=f"{scene_id}:{alert.id}:{alert.code}",
            source_version=f"{session.provider}:{session.capture_date.isoformat()}",
            action_code=f"field_scouting_{alert.category}",
            suggestion_time=now,
            expires_at=payload.expires_at,
            source_verified=False,
        )
        action = await self.actions.register_source_action(user, payload.farm_id, source)
        if action is None:
            raise OrganicAdvisoryNotAllowedError()
        return SatelliteScoutingOut(
            action=ActionOut.from_row(action),
            trigger=alert.code,
            scene_id=scene_id,
            checklist=checklist,
            limitation=(
                "Satellite evidence only identifies where to inspect. It does not "
                "diagnose a disease, nutrient deficiency, or treatment need."
            ),
        )
