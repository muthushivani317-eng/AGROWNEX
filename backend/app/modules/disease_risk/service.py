from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.farms.repositories import FarmRepository
from app.modules.growth.stage_service import StageTrackingService
from app.modules.weather.service import WeatherService

from .engine import RiskInputs, RiskOutcome, evaluate_risk
from .models import DiseaseRiskAlert
from .registry import RulePackRegistry
from .repository import DiseaseRiskRepository

# Deliberately empty (found in the 2026-08 pre-release audit as "the alert
# feature is permanently dead"). This is fail-closed by design, not a bug:
# every RulePack drives a real weather-triggered disease-risk alert shown to a
# farmer (e.g. "conditions favour Sigatoka leaf spot this week"), which means
# each one needs real, source-cited epidemiological thresholds -- crop,
# disease, region/season, the specific temperature/humidity/rainfall
# conditions that raise risk, reviewed and approved by an agronomist against a
# citable official source (RulePack.source_references, .reviewer_id,
# .approval_status == "VERIFIED"; see schemas.py). That is safety-critical
# agricultural content this codebase must not fabricate (docs/CLAUDE.md), so
# until real verified RulePack entries exist, ACTIVE_RULE_REGISTRY correctly
# stays empty and every evaluate() call returns NO_VERIFIED_RULE_AVAILABLE
# (farmer_message_key="diseaseRisk.noVerifiedRule") instead of guessing.
# To activate: construct RulePackRegistry([...]) with one or more RulePack
# instances that pass RulePackRegistry._executable (VERIFIED, unexpired,
# content-hash-matched) and wire the result in here.
ACTIVE_RULE_REGISTRY = RulePackRegistry([])


class DiseaseRiskService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        registry: RulePackRegistry | None = None,
        weather: WeatherService | None = None,
    ) -> None:
        self.session = session
        self.farms = FarmRepository(session)
        self.repo = DiseaseRiskRepository(session)
        self.registry = registry or ACTIVE_RULE_REGISTRY
        self.weather = weather or WeatherService(session)

    async def _farm(self, user: User, farm_id: uuid.UUID):
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise PermissionError("FARM_NOT_OWNED")
        return farm

    async def evaluate(
        self, user: User, farm_id: uuid.UUID, crop_cycle_id: str | None, key: str
    ) -> DiseaseRiskAlert:
        existing = await self.repo.by_key(user.id, key)
        if existing:
            return existing
        farm = await self._farm(user, farm_id)
        now = datetime.now(UTC)
        crop = (farm.crop or "unknown").strip().lower()
        region = farm.location.district if farm.location else None
        pack = self.registry.find(crop_id=crop, region=region, season=None)
        stage = None
        stage_confirmed = False
        weather_values: dict[str, float] = {}
        weather_source = "missing"
        observed_at = None
        if pack is not None:
            state = (
                await StageTrackingService(self.session).current(user, farm_id, crop_cycle_id)
                if crop_cycle_id
                else None
            )
            stage = state.confirmed_stage if state else None
            stage_confirmed = bool(
                state and state.state in {"confirmed", "corrected", "completed"} and stage
            )
            if stage_confirmed:
                try:
                    bundle = await self.weather.get_by_farm(user, farm_id)
                    current = bundle.current
                    weather_values = {
                        k: v
                        for k, v in {
                            "temperature_c": current.temperature_c,
                            "humidity_pct": current.humidity_pct,
                            "precipitation_mm": current.precipitation_mm,
                            "wind_speed_kmh": current.wind_speed_kmh,
                        }.items()
                        if v is not None
                    }
                    weather_source = (
                        bundle.source if bundle.source in {"live", "cached"} else "live"
                    )
                    observed_at = datetime.fromisoformat(current.time.replace("Z", "+00:00"))
                except Exception:
                    weather_source = "missing"
        result = evaluate_risk(
            pack,
            RiskInputs(
                crop,
                stage,
                stage_confirmed,
                weather_values,
                weather_source,
                observed_at,
                region,
                None,
                now,
            ),
        )
        status = (
            "NO_VERIFIED_RULE_AVAILABLE"
            if result.outcome == RiskOutcome.RULE_PACK_UNAVAILABLE
            else result.outcome.value
        )
        message = (
            "diseaseRisk.noVerifiedRule"
            if status == "NO_VERIFIED_RULE_AVAILABLE"
            else (
                "diseaseRisk.conditionsPresent"
                if status == "RISK_CONDITIONS_PRESENT"
                else "diseaseRisk.insufficientData"
            )
        )
        row = DiseaseRiskAlert(
            user_id=user.id,
            farm_id=farm_id,
            crop=crop,
            disease_key=pack.disease_id if pack else None,
            status=status,
            risk_level="HIGH" if status == "RISK_CONDITIONS_PRESENT" else None,
            confidence="verified_rule_evidence" if pack else "unavailable",
            weather_factors=result.matched_conditions,
            weather_source=weather_source,
            weather_observed_at=observed_at,
            crop_stage=stage,
            generated_at=now,
            valid_until=now + timedelta(hours=pack.alert_expiry_hours) if pack else None,
            rule_pack_id=pack.pack_id if pack else None,
            rule_version=pack.version if pack else None,
            rule_verification_status="VERIFIED" if pack else "UNAVAILABLE",
            farmer_message_key=message,
            evidence=result.evidence_used,
            missing_inputs=result.missing_fields,
            idempotency_key=key,
            notification_emitted=status == "RISK_CONDITIONS_PRESENT",
        )
        return await self.repo.add(row)

    async def current(self, user: User, farm_id: uuid.UUID):
        await self._farm(user, farm_id)
        return await self.repo.latest(user.id, farm_id)

    async def history(self, user: User, farm_id: uuid.UUID | None, limit: int, offset: int):
        if farm_id:
            await self._farm(user, farm_id)
        return await self.repo.history(user.id, farm_id, limit, offset)

    async def get(self, user: User, risk_id: uuid.UUID):
        row = await self.repo.get(user.id, risk_id)
        if row is None:
            raise LookupError("DISEASE_RISK_NOT_FOUND")
        return row

    async def acknowledge(self, user: User, risk_id: uuid.UUID):
        row = await self.get(user, risk_id)
        row.acknowledged_at = row.acknowledged_at or datetime.now(UTC)
        await self.session.flush()
        return row
