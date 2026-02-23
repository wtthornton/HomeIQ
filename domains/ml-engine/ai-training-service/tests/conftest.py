"""
Pytest configuration and fixtures for AI Training Service

Epic 39, Story 39.4: Training Service Testing & Validation
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models import Base, TrainingRun
from src.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session using in-memory SQLite.
    
    Each test gets a fresh database.
    """
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
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
        "started_at": datetime.utcnow(),
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
        "started_at": datetime.utcnow(),
        "finished_at": datetime.utcnow(),
        "output_dir": "/tmp/test_output",
        "run_identifier": "test_run_20250101_120000",
        "triggered_by": "test_user",
        "dataset_size": 100,
        "base_model": "google/flan-t5-small",
        "final_loss": 0.5,
    }

