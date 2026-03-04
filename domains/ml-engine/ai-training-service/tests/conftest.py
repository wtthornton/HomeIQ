"""
Pytest configuration and fixtures for AI Training Service

Epic 39, Story 39.4: Training Service Testing & Validation
"""

import os
from datetime import UTC, datetime
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.database.models import Base

# Phase 2: event_loop fixture removed — pytest-asyncio 1.3.0 manages event loops internally


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session using PostgreSQL.

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
    
    # Create all tables
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
def sample_training_run_data():
    """Sample training run data for testing."""
    return {
        "training_type": "soft_prompt",
        "status": "queued",
        "started_at": datetime.now(UTC),
        "output_dir": "/tmp/test_output",
        "run_identifier": "test_run_20250101_120000",
        "triggered_by": "test_user",
    }


@pytest.fixture
def sample_training_run_completed_data():
    """Sample completed training run data for testing."""
    return {
        "training_type": "soft_prompt",
        "status": "completed",
        "started_at": datetime.now(UTC),
        "finished_at": datetime.now(UTC),
        "output_dir": "/tmp/test_output",
        "run_identifier": "test_run_20250101_120000",
        "triggered_by": "test_user",
        "dataset_size": 100,
        "base_model": "google/flan-t5-small",
        "final_loss": 0.5,
    }

