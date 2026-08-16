from app.api.v1.router import api_router
from app.modules.calendar.registry import ACTIVE_CROP_STAGE_REGISTRY


def test_calendar_router_is_registered_with_required_routes() -> None:
    paths = {route.path for route in api_router.routes}
    assert {
        "/calendar",
        "/calendar/generate",
        "/calendar/today",
        "/calendar/upcoming",
        "/calendar/summary",
        "/calendar/{farm_id}",
        "/calendar/events/{event_id}",
    }.issubset(paths)


def test_production_registry_contains_no_claimed_verified_agronomy() -> None:
    assert ACTIVE_CROP_STAGE_REGISTRY.active_count == 0
    assert ACTIVE_CROP_STAGE_REGISTRY.unverified_count == 0
