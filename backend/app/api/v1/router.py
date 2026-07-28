"""Aggregate v1 API router (docs/API_CONTRACT.md → /api/v1)."""
from __future__ import annotations

from fastapi import APIRouter

from app.crop_runtime.router import router as crop_runtime_router
from app.api.v1.health import router as health_router
from app.modules.admin.router import router as admin_router
from app.modules.ai.router import router as ai_router
from app.modules.auth.router import router as auth_router
from app.modules.calendar.router import router as calendar_router
from app.modules.disease.router import router as disease_router
from app.modules.experts.router import (
    consultations_router,
    experts_router,
)
from app.modules.farmers.router import router as farmers_router
from app.modules.farms.router import router as farms_router
from app.modules.growth.router import router as growth_router
from app.modules.intelligence.router import router as intelligence_router
from app.modules.market.router import router as market_router
from app.modules.memory.router import router as memory_router
from app.modules.notifications.router import router as notifications_router
from app.modules.nutrient.router import router as nutrient_router
from app.modules.produce.router import router as produce_router
from app.modules.satellite.router import router as satellite_router
from app.modules.schemes.router import router as schemes_router
from app.modules.soil.router import router as soil_router
from app.modules.weather.router import router as weather_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(farmers_router)
api_router.include_router(farms_router)
api_router.include_router(weather_router)
api_router.include_router(ai_router)
api_router.include_router(disease_router)
api_router.include_router(crop_runtime_router)
api_router.include_router(calendar_router)
api_router.include_router(market_router)
api_router.include_router(growth_router)
api_router.include_router(schemes_router)
api_router.include_router(produce_router)
api_router.include_router(notifications_router)
api_router.include_router(experts_router)
api_router.include_router(consultations_router)
api_router.include_router(soil_router)
api_router.include_router(satellite_router)
api_router.include_router(nutrient_router)
api_router.include_router(intelligence_router)
api_router.include_router(memory_router)
api_router.include_router(admin_router)
