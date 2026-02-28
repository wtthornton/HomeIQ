"""
Pytest configuration and fixtures for Proactive Agent Service tests
"""

from __future__ import annotations

import os

import pytest
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.database import Base
from src.models import Suggestion

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
