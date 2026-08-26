from app.api.v1.router import api_router
from app.modules.calendar.registry import ACTIVE_CROP_STAGE_REGISTRY
from fastapi import FastAPI


def test_calendar_router_is_registered_with_required_routes() -> None:
    app = FastAPI()
    app.include_router(api_router)
    paths = set(app.openapi()["paths"])
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
    # Updated 2026-08-18: all 12 crops in the app's crop list (COMMON_CROPS in
    # agrow-ai/constants/crops.ts) now have real, cited schedules under
    # app/modules/calendar/data/verified_schedules/ -- paddy.json and
    # chilli.json (status=SOURCED_PUBLIC_REFERENCE, compiled from TNAU
    # Agritech Portal / ICAR-CCARI sources), plus 10 newly added crops
    # (sugarcane, groundnut, cotton, maize, banana, coconut, tomato,
    # brinjal, turmeric, millet) compiled from TNAU Agritech Portal / ICAR
    # sources, also status=SOURCED_PUBLIC_REFERENCE and not yet personally
    # reviewed by an independent agronomist for AgrowAI (see that
    # directory's README). Coconut is deliberately scoped to its
    # establishment phase (years 1-2) only, since it is a perennial crop
    # that does not fit the 2-year schedule window used for annuals; the
    # "millet" crop id is represented as pearl millet / cumbu, the variety
    # grown in Tamil Nadu.
    # This is the intended signal from that README: once a real entry lands,
    # this assertion updates to match, rather than staying at 0 forever.
    assert ACTIVE_CROP_STAGE_REGISTRY.active_count == 12
    assert ACTIVE_CROP_STAGE_REGISTRY.unverified_count == 0
