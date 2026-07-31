"""Database URL adaptation for async SQLAlchemy consumers."""
from __future__ import annotations

import logging

import pytest
from app.core.config import Settings, normalize_async_database_url
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        (
            "postgresql://user:password@host:5432/database",
            "postgresql+asyncpg://user:password@host:5432/database",
        ),
        (
            "postgres://user:password@host:5432/database",
            "postgresql+asyncpg://user:password@host:5432/database",
        ),
        (
            "postgresql+asyncpg://user:password@host:5432/database",
            "postgresql+asyncpg://user:password@host:5432/database",
        ),
        (
            "postgresql+psycopg://user:password@host:5432/database",
            "postgresql+psycopg://user:password@host:5432/database",
        ),
        (
            "sqlite+aiosqlite:///./test.db",
            "sqlite+aiosqlite:///./test.db",
        ),
    ],
)
def test_normalizes_only_plain_postgresql_schemes(configured: str, expected: str):
    assert normalize_async_database_url(configured) == expected


def test_preserves_query_parameters_verbatim():
    configured = "postgresql://user:password@host:5432/database?sslmode=require&x=one%20two"

    assert normalize_async_database_url(configured) == (
        "postgresql+asyncpg://user:password@host:5432/database"
        "?sslmode=require&x=one%20two"
    )


def test_settings_exposes_normalized_async_url_without_mutating_configured_url():
    configured = "postgresql://user:password@host:5432/database?sslmode=require"
    settings = Settings(database_url=configured)

    assert settings.database_url == configured
    assert settings.async_database_url.startswith("postgresql+asyncpg://")
    assert settings.async_database_url.endswith("?sslmode=require")


def test_credentials_are_not_logged(caplog: pytest.LogCaptureFixture):
    configured = "postgresql://sensitive-user:sensitive-password@host:5432/database"

    with caplog.at_level(logging.DEBUG):
        normalize_async_database_url(configured)

    assert "sensitive-user" not in caplog.text
    assert "sensitive-password" not in caplog.text


@pytest.mark.asyncio
async def test_normalized_url_creates_async_compatible_engine():
    engine = create_async_engine(
        normalize_async_database_url("postgresql://user:password@host:5432/database")
    )
    try:
        assert engine.dialect.is_async is True
        assert engine.url.drivername == "postgresql+asyncpg"
    finally:
        await engine.dispose()
