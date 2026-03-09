"""
Pytest configuration and fixtures for Proactive Agent Service tests
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest

# Add service root and src/ directory to sys.path for imports
_service_root = str(Path(__file__).resolve().parent.parent)
_service_src = str(Path(__file__).resolve().parent.parent / "src")
if _service_root not in sys.path:
    sys.path.insert(0, _service_root)
if _service_src not in sys.path:
    sys.path.insert(0, _service_src)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.database import Base

# Phase 2: event_loop fixture removed — pytest-asyncio 1.3.0 manages event loops internally


@pytest.fixture(scope="function")
async def mock_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a mock database session using PostgreSQL.

    Each test gets a fresh database.
    """
    # Use PostgreSQL for tests
    test_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq_test",
    )
    engine = create_async_engine(
        test_url,
        echo=False,
    )
    
    # Create tables using SQLAlchemy models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create session for test
    async with async_session_maker() as session:
        yield session
    
    # Cleanup
    await engine.dispose()
