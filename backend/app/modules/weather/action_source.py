"""Weather Mission adapter for the shared Action Verification workflow."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.modules.action_verification.source_adapter import SourceAction
from app.modules.weather.schemas import WeatherBundle


def weather_source_action(farm_id: uuid.UUID, bundle: WeatherBundle) -> SourceAction | None:
    mission = bundle.mission
    if mission.source_insight_code is None or not mission.primary_action.strip():
        return None
    fetched = datetime.fromisoformat(bundle.fetched_at.replace("Z", "+00:00"))
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=UTC)
    record_id = f"{farm_id}:{fetched.date().isoformat()}:{mission.source_insight_code}"
    return SourceAction(
        source_feature="weather_to_action",
        source_record_id=record_id,
        source_version=bundle.fetched_at,
        action_code=mission.primary_action,
        suggestion_time=fetched,
        due_at=fetched + timedelta(hours=24),
        expires_at=fetched + timedelta(hours=36),
        # Translation does not constitute expert verification.
        source_verified=False,
    )
