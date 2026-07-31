"""Alembic environment (async) — reads settings and model metadata from the app.

Every schema change goes through a reversible migration (docs/DATABASE_SCHEMA.md,
docs/DEPLOYMENT.md). Never edit production tables manually.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from app.core.config import settings

# Import models so they register on Base.metadata for autogenerate.
from app.modules.ai import models as _ai_models  # noqa: F401
from app.modules.auth import models as _auth_models  # noqa: F401
from app.modules.auth import profile_models as _profile_models  # noqa: F401
from app.modules.auth import rbac_models as _rbac_models  # noqa: F401
from app.modules.calendar import models as _calendar_models  # noqa: F401
from app.modules.disease import models as _disease_models  # noqa: F401
from app.modules.farms import models as _farm_models  # noqa: F401
from app.modules.intelligence import models as _intelligence_models  # noqa: F401
from app.modules.memory import models as _memory_models  # noqa: F401
from app.modules.nutrient import models as _nutrient_models  # noqa: F401
from app.shared.base_model import Base
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config
config.set_main_option("sqlalchemy.url", settings.async_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.async_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
