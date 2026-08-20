"""
Pytest configuration and fixtures for Proactive Agent Service tests
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest_asyncio

# Add service root and src/ directory to sys.path for imports
_service_root = str(Path(__file__).resolve().parent.parent)
_service_src = str(Path(__file__).resolve().parent.parent / "src")
if _service_root not in sys.path:
    sys.path.insert(0, _service_root)
if _service_src not in sys.path:
    sys.path.insert(0, _service_src)

from typing import TYPE_CHECKING

from homeiq_data import create_pg_engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.database import Base, _schema

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Phase 2: event_loop fixture removed — pytest-asyncio 1.3.0 manages event loops internally


@pytest_asyncio.fixture(scope="function")
async def mock_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Real PostgreSQL session, pinned to the service schema like production.

    The models' foreign keys are unqualified (``REFERENCES suggestions``), so
    the engine must carry the same search_path DatabaseManager sets in prod;
    a bare engine resolves ``suggestions`` through the database default
    search_path to ``automation.suggestions`` (integer id) and create_all
    fails on the FK type. Tables are dropped after each test so runs that
    share one database do not leak rows into each other.
    """
    test_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq_test",
    )
    engine = create_pg_engine(test_url, schema=_schema, pool_size=1, max_overflow=0)

    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_schema}"))
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
