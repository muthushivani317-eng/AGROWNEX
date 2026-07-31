"""Async SQLAlchemy engine & session (docs/BACKEND_ARCHITECTURE.md).

Only repositories talk to the database. Sessions are provided to the service
layer via FastAPI dependency injection.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_engine_options: dict[str, object] = {
    "echo": settings.db_echo,
    "pool_pre_ping": True,
    "future": True,
}
if not settings.database_url.startswith("sqlite"):
    _engine_options.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
    )

engine = create_async_engine(settings.database_url, **_engine_options)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional session."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
