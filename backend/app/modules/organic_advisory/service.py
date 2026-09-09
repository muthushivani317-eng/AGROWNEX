from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.action_verification.models import ActionWorkflow
from app.modules.action_verification.schemas import ActionOut
from app.modules.action_verification.service import ActionVerificationService
from app.modules.action_verification.source_adapter import SourceAction
from app.modules.auth.models import User
from app.modules.farms.exceptions import FarmNotFoundError
from app.modules.farms.repositories import FarmRepository
from app.modules.organic.repositories import OrganicRepository
from app.modules.satellite.constants import CLOUD_USABLE_MAX, SessionStatus
from app.modules.satellite.models import SatelliteAlert, SatelliteSession
from app.modules.weather.constants import SPRAY_MAX_RAIN_PROB_PCT, SPRAY_MAX_WIND_KMH
from app.modules.weather.service import WeatherService

from .exceptions import OrganicAdvisoryNotAllowedError, OrganicAdvisoryReferenceError
from .models import OrganicActionReschedule, OrganicNotificationIntent, OrganicWeatherSnapshot
from .schemas import (
    SatelliteFindingIn,
    SatelliteFindingOut,
    SatelliteScoutingIn,
    SatelliteScoutingOut,
    TrustedWeatherGateIn,
    TrustedWeatherGateOut,
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
        "inspect_crop_vigor_pattern",
        "look_for_visible_pest_or_disease_symptoms",
        "look_for_visible_nutrient_symptoms",
        "record_photos_and_field_notes",
    ],
    "moisture": [
        "inspect_soil_moisture",
        "check_irrigation_and_drainage",
        "check_mulch_coverage",
        "record_photos_and_field_notes",
    ],
    "variation": [
        "inspect_flagged_field_zones",
        "check_weed_pressure",
        "check_moisture_and_mulch_uniformity",
        "check_amendment_distribution",
        "record_photos_and_field_notes",
    ],
    "seasonal": [
        "confirm_crop_stage",
        "inspect_physical_crop_condition",
        "record_photos_and_field_notes",
    ],
}


class OrganicAdvisoryService:
    def __init__(self, session: AsyncSession, *, weather: WeatherService | None = None) -> None:
        self.session = session
        self.actions = ActionVerificationService(session)
        self.organic = OrganicRepository(session)
        self.weather = weather
        self.farms = FarmRepository(session)

    async def weather_metrics(self, user: User, farm_id: uuid.UUID) -> dict:
        """Owner-scoped aggregate telemetry; no coordinates, snapshots, or identifiers."""
        if await self.farms.get_for_user(farm_id, user.id) is None:
            raise FarmNotFoundError()

        async def count(model, *criteria):
            return int(
                await self.session.scalar(
                    select(func.count(model.id)).where(
                        model.user_id == user.id, model.farm_id == farm_id, *criteria
                    )
                )
                or 0
            )

        return {
            "farm_id": farm_id,
            "snapshot_count": await count(OrganicWeatherSnapshot),
            "reschedule_count": await count(OrganicActionReschedule),
            "pending_notification_intents": await count(
                OrganicNotificationIntent, OrganicNotificationIntent.status == "pending"
            ),
        }

    async def trusted_weather_gate(
        self, user: User, payload: TrustedWeatherGateIn
    ) -> TrustedWeatherGateOut:
        """Fetch and persist provider weather; the request contains no weather claims."""
        if not settings.organic_trusted_weather_enabled:
            raise OrganicAdvisoryNotAllowedError()
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "farm_id": str(payload.farm_id),
                    "action_workflow_id": str(payload.action_workflow_id),
                    "organic_input_id": str(payload.organic_input_id),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        existing = await self.session.scalar(
            select(OrganicActionReschedule).where(
                OrganicActionReschedule.user_id == user.id,
                OrganicActionReschedule.idempotency_key == payload.idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise ValueError("IDEMPOTENCY_CONFLICT")
            intent = await self.session.scalar(
                select(OrganicNotificationIntent).where(
                    OrganicNotificationIntent.reschedule_id == existing.id
                )
            )
            return TrustedWeatherGateOut(
                original_action_id=existing.action_workflow_id,
                weather_snapshot_id=existing.weather_snapshot_id,
                reschedule_id=existing.id,
                notification_intent_id=intent.id if intent else None,
                signal_code=existing.signal_code,
                rescheduled_for=existing.rescheduled_for,
                source_verified=True,
                data_state="persisted",
            )
        original = await self.session.get(ActionWorkflow, payload.action_workflow_id)
        if (
            original is None
            or original.is_deleted
            or original.user_id != user.id
            or original.farm_id != payload.farm_id
            or not original.source_module.startswith("organic_")
        ):
            raise OrganicAdvisoryReferenceError()
        if original.status not in {"suggested", "viewed", "deferred"} or (
            original.expires_at is not None and original.expires_at <= datetime.now(UTC)
        ):
            raise OrganicAdvisoryNotAllowedError()
        item = await self.organic.approved_input(payload.organic_input_id, date.today())
        if item is None:
            raise OrganicAdvisoryReferenceError()
        if self.weather is None:
            raise OrganicAdvisoryNotAllowedError()
        bundle = await self.weather.get_by_farm(user, payload.farm_id)
        now = datetime.now(UTC)
        fetched_at = datetime.fromisoformat(bundle.fetched_at.replace("Z", "+00:00"))
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)
        if fetched_at > now + timedelta(minutes=5) or fetched_at < now - timedelta(hours=2):
            raise OrganicAdvisoryNotAllowedError()
        allowed = set((item.limitations or {}).get("weather_gates", []))
        signal = next(
            (
                insight.code
                for insight in bundle.insights
                if insight.code in _WEATHER_GATE_ACTIONS and insight.code in allowed
            ),
            None,
        )
        snapshot_data = bundle.model_dump(mode="json")
        snapshot = OrganicWeatherSnapshot(
            user_id=user.id,
            farm_id=payload.farm_id,
            provider=bundle.source,
            provider_fetched_at=fetched_at,
            valid_until=min(fetched_at + timedelta(hours=24), now + timedelta(hours=24)),
            payload_hash=hashlib.sha256(
                json.dumps(snapshot_data, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            snapshot_json=snapshot_data,
        )
        self.session.add(snapshot)
        await self.session.flush()
        if signal is None:
            return TrustedWeatherGateOut(
                original_action_id=original.id,
                weather_snapshot_id=snapshot.id,
                reschedule_id=None,
                notification_intent_id=None,
                signal_code=None,
                rescheduled_for=None,
                source_verified=True,
                data_state=bundle.data_state,
            )
        # A single dry hour does not prove a heavy-rain event has ended; keep
        # timing unknown until a dedicated sustained-clear rule is approved.
        if signal in {"heavy_rain.expected", "heavy_rain.severe"}:
            return TrustedWeatherGateOut(
                original_action_id=original.id,
                weather_snapshot_id=snapshot.id,
                reschedule_id=None,
                notification_intent_id=None,
                signal_code=signal,
                rescheduled_for=None,
                source_verified=True,
                data_state=bundle.data_state,
            )
        safe_after = None
        for point in bundle.hourly:
            point_time = datetime.fromisoformat(point.time.replace("Z", "+00:00"))
            if point_time.tzinfo is None:
                point_time = point_time.replace(tzinfo=UTC)
            dry = (
                point.precipitation_probability_pct is not None
                and point.precipitation_probability_pct <= SPRAY_MAX_RAIN_PROB_PCT
                and point.precipitation_mm is not None
                and point.precipitation_mm == 0
            )
            calm = point.wind_speed_kmh is not None and point.wind_speed_kmh <= SPRAY_MAX_WIND_KMH
            if now < point_time <= snapshot.valid_until and dry and calm:
                safe_after = point_time
                break
        if safe_after is None:
            return TrustedWeatherGateOut(
                original_action_id=original.id,
                weather_snapshot_id=snapshot.id,
                reschedule_id=None,
                notification_intent_id=None,
                signal_code=signal,
                rescheduled_for=None,
                source_verified=True,
                data_state=bundle.data_state,
            )
        history = OrganicActionReschedule(
            user_id=user.id,
            farm_id=payload.farm_id,
            action_workflow_id=original.id,
            weather_snapshot_id=snapshot.id,
            signal_code=signal,
            prior_due_at=original.due_at,
            rescheduled_for=safe_after,
            idempotency_key=payload.idempotency_key,
            request_fingerprint=fingerprint,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(history)
                await self.session.flush()
        except IntegrityError:
            winner = await self.session.scalar(
                select(OrganicActionReschedule).where(
                    OrganicActionReschedule.user_id == user.id,
                    OrganicActionReschedule.idempotency_key == payload.idempotency_key,
                )
            )
            if winner is None or winner.request_fingerprint != fingerprint:
                raise ValueError("IDEMPOTENCY_CONFLICT") from None
            winner_intent = await self.session.scalar(
                select(OrganicNotificationIntent).where(
                    OrganicNotificationIntent.reschedule_id == winner.id
                )
            )
            return TrustedWeatherGateOut(
                original_action_id=winner.action_workflow_id,
                weather_snapshot_id=winner.weather_snapshot_id,
                reschedule_id=winner.id,
                notification_intent_id=winner_intent.id if winner_intent else None,
                signal_code=winner.signal_code,
                rescheduled_for=winner.rescheduled_for,
                source_verified=True,
                data_state="persisted",
            )
        original.due_at = safe_after
        intent = OrganicNotificationIntent(
            user_id=user.id,
            farm_id=payload.farm_id,
            reschedule_id=history.id,
            dedup_key=f"organic-weather:{history.id}",
            event_type="organic_action_rescheduled",
            scheduled_for=now,
        )
        self.session.add(intent)
        await self.session.flush()
        return TrustedWeatherGateOut(
            original_action_id=original.id,
            weather_snapshot_id=snapshot.id,
            reschedule_id=history.id,
            notification_intent_id=intent.id,
            signal_code=signal,
            rescheduled_for=safe_after,
            source_verified=True,
            data_state=bundle.data_state,
        )

    async def weather_gate(
        self, user: User, payload: WeatherOrganicGateIn
    ) -> WeatherOrganicGateOut:
        original = await self.session.get(ActionWorkflow, payload.action_workflow_id)
        if (
            original is None
            or original.is_deleted
            or original.user_id != user.id
            or original.farm_id != payload.farm_id
        ):
            raise OrganicAdvisoryReferenceError()
        if not original.source_module.startswith("organic_") or original.status not in {
            "suggested",
            "viewed",
            "deferred",
        }:
            raise OrganicAdvisoryNotAllowedError()
        item = await self.organic.approved_input(payload.organic_input_id, date.today())
        if item is None:
            raise OrganicAdvisoryReferenceError()

        # The catalogue must explicitly allow this gate. Weather alone never
        # creates agronomy. Supported entries use limitations.weather_gates.
        allowed = {str(code) for code in (item.limitations or {}).get("weather_gates", [])}
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
        if alert is None or alert.user_id != user.id or alert.farm_id != payload.farm_id:
            raise OrganicAdvisoryReferenceError()
        session = await self.session.get(SatelliteSession, alert.session_id)
        if (
            session is None
            or session.user_id != user.id
            or session.farm_id != payload.farm_id
            or session.is_deleted
            or session.status != SessionStatus.AVAILABLE.value
            or session.is_sample
            or session.capture_date is None
            or session.cloud_cover is None
            or session.cloud_cover > CLOUD_USABLE_MAX
        ):
            raise OrganicAdvisoryNotAllowedError()
        checklist = _SCOUTING_CHECKLISTS.get(alert.category)
        if checklist is None:
            # Imagery-availability alerts must never become field diagnoses/tasks.
            raise OrganicAdvisoryNotAllowedError()
        now = datetime.now(UTC)
        if payload.expires_at.astimezone(UTC) <= now or payload.expires_at.astimezone(
            UTC
        ) > now + timedelta(days=7):
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

    async def record_satellite_findings(
        self, user: User, action_id: uuid.UUID, payload: SatelliteFindingIn
    ) -> SatelliteFindingOut:
        action = await self.session.get(ActionWorkflow, action_id)
        if (
            action is None
            or action.user_id != user.id
            or action.is_deleted
            or action.source_module != "satellite_field_scouting"
        ):
            raise OrganicAdvisoryReferenceError()
        if action.status not in {"suggested", "viewed", "deferred"} or (
            action.expires_at is not None
            and action.expires_at.replace(tzinfo=action.expires_at.tzinfo or UTC)
            <= datetime.now(UTC)
        ):
            raise OrganicAdvisoryNotAllowedError()
        from app.modules.organic_logbook.schemas import OrganicLogCreateIn
        from app.modules.organic_logbook.service import OrganicLogbookService

        observations = ",".join(payload.observations)
        finding_digest = hashlib.sha256(payload.idempotency_key.encode()).hexdigest()
        note = f"Farmer observations: {observations}"
        if payload.note:
            note = f"{note}\n{payload.note}"
        entry = await OrganicLogbookService(self.session).create(
            user,
            OrganicLogCreateIn(
                farm_id=action.farm_id,
                action_workflow_id=action.id,
                practice_type="scouting",
                practice_code="satellite_farmer_findings",
                input_reference=f"observations:{hashlib.sha256(observations.encode()).hexdigest()}",
                occurred_at=datetime.now(UTC),
                note=note,
                idempotency_key=f"satellite-finding:{finding_digest}",
            ),
        )
        follow_up = None
        if payload.observations != ["nothing_observed"]:
            follow_up = await self.actions.register_source_action(
                user,
                action.farm_id,
                SourceAction(
                    source_feature="satellite_scouting_followup",
                    source_record_id=str(entry.id),
                    source_version=action.source_version,
                    action_code="review_farmer_reported_field_findings",
                    suggestion_time=datetime.now(UTC),
                    source_verified=False,
                    crop_cycle_id=action.crop_cycle_id,
                ),
            )
        return SatelliteFindingOut(
            log_entry_id=entry.id,
            follow_up_action=ActionOut.from_row(follow_up) if follow_up else None,
        )
