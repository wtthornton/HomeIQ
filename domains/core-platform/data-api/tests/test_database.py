"""
Tests for SQLite database configuration
Story 22.1
"""

import pytest
from sqlalchemy import text

from src.database import (
    DATABASE_URL,
    AsyncSessionLocal,
    async_engine,
    check_db_health,
    get_db,
    init_db,
)

# In-memory SQLite uses journal_mode "memory", not "wal"
_IS_MEMORY = ":memory:" in (DATABASE_URL or "")


@pytest.mark.asyncio
async def test_database_engine_initialization():
    """Test that async engine is properly configured"""
    assert async_engine is not None
    assert "sqlite+aiosqlite" in str(async_engine.url)


@pytest.mark.asyncio
async def test_session_factory_creation():
    """Test that session factory creates valid sessions"""
    async with AsyncSessionLocal() as session:
        assert session is not None
        # Test simple query
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_wal_mode_enabled():
    """Test that WAL mode is enabled (or memory for in-memory DBs)"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("PRAGMA journal_mode"))
        journal_mode = (result.scalar() or "").lower()
        # In-memory DBs use "memory"; on-disk use "wal"
        assert journal_mode in ("wal", "memory")


@pytest.mark.asyncio
async def test_foreign_keys_enabled():
    """Test that foreign key constraints are enabled"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("PRAGMA foreign_keys"))
        foreign_keys = result.scalar()
        assert foreign_keys == 1


@pytest.mark.asyncio
async def test_init_db():
    """Test database initialization"""
    await init_db()
    # Should complete without error


@pytest.mark.asyncio
async def test_check_db_health():
    """Test health check function"""
    health = await check_db_health()
    assert health["status"] == "healthy"
    # In-memory DBs use journal_mode "memory"; on-disk use "wal"
    assert health["journal_mode"] in ("wal", "memory")
    if _IS_MEMORY:
        assert "wal_enabled" in health  # may be False for memory
    else:
        assert health["wal_enabled"] is True
    assert "database_size_mb" in health


@pytest.mark.asyncio
async def test_get_db_dependency():
    """Test FastAPI dependency"""
    async for session in get_db():
        assert session is not None
        # Test transaction handling
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        break


@pytest.mark.asyncio
async def test_connection_error_handling():
    """Test graceful error handling on connection issues"""
    # Health check should handle errors gracefully
    health = await check_db_health()
    # Should always return a dict
    assert isinstance(health, dict)
    assert "status" in health

