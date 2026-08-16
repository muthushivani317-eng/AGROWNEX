"""Shared test fixtures — an in-memory async DB with the auth schema seeded."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio

# Import model modules so every table registers on Base.metadata.
from app.modules.admin import models as _admin_models  # noqa: F401
from app.modules.ai import models as _ai_models  # noqa: F401
from app.modules.auth import models as _models  # noqa: F401
from app.modules.auth import profile_models as _profile_models  # noqa: F401
from app.modules.auth import rbac_models as _rbac_models  # noqa: F401
from app.modules.auth.constants import RoleName
from app.modules.auth.rbac_models import Role
from app.modules.calendar import models as _calendar_models  # noqa: F401
from app.modules.disease import models as _disease_models  # noqa: F401
from app.modules.experts import models as _expert_models  # noqa: F401
from app.modules.farms import models as _farm_models  # noqa: F401
from app.modules.growth import models as _growth_models  # noqa: F401
from app.modules.intelligence import models as _intelligence_models  # noqa: F401
from app.modules.market import models as _market_models  # noqa: F401
from app.modules.memory import models as _memory_models  # noqa: F401
from app.modules.notifications import models as _notification_models  # noqa: F401
from app.modules.nutrient import models as _nutrient_models  # noqa: F401
from app.modules.produce import models as _produce_models  # noqa: F401
from app.modules.satellite import models as _satellite_models  # noqa: F401
from app.modules.schemes import models as _scheme_models  # noqa: F401
from app.modules.soil import models as _soil_models  # noqa: F401
from app.shared.base_model import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest_asyncio.fixture
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """A sessionmaker bound to a fresh in-memory engine.

    Exposed so tests can point a background task's own session factory (e.g.
    ``app.modules.market.service.SessionLocal``) at the same in-memory engine
    the request-scoped ``db_session`` uses. ``StaticPool`` keeps a single shared
    connection, so writes committed on one session are visible to the other.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        # Seed default roles (the migration does this in production).
        for name in RoleName:
            session.add(Role(role_name=name.value))
        await session.flush()
        yield session
