"""
Pytest configuration and fixtures for AI Pattern Service

Epic 39, Story 39.8: Pattern Service Testing & Validation
"""

import os
from datetime import UTC
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Note: Pattern and SynergyOpportunity models are in shared database
# For testing, we'll use mock models or raw SQL
from src.database import get_db
from src.main import app

# Phase 2: event_loop fixture removed — pytest-asyncio 1.3.0 manages event loops internally


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session using PostgreSQL.

    Each test gets a fresh database.
    Note: Pattern and SynergyOpportunity tables are in shared database,
    so we'll use raw SQL or mock models for testing.
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

    # Create basic tables (Pattern and SynergyOpportunity would be in shared DB)
    # For testing, we'll create minimal schema or use mocks
    async with engine.begin() as conn:
        # Create patterns table if needed
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS patterns (
                id SERIAL PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                device_id TEXT NOT NULL,
                pattern_metadata JSONB,
                confidence REAL NOT NULL,
                occurrences INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        )
        # Create synergy_opportunities table if needed
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS synergy_opportunities (
                id SERIAL PRIMARY KEY,
                synergy_id TEXT UNIQUE NOT NULL,
                synergy_type TEXT NOT NULL,
                device_ids TEXT NOT NULL,
                opportunity_metadata JSONB,
                impact_score REAL NOT NULL,
                complexity TEXT NOT NULL,
                confidence REAL NOT NULL,
                area TEXT,
                explanation JSONB,
                context_breakdown JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        )
        # Create synergy_feedback table for RL feedback loop
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS synergy_feedback (
                id SERIAL PRIMARY KEY,
                synergy_id TEXT NOT NULL,
                accepted BOOLEAN NOT NULL,
                feedback_text TEXT,
                rating INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (synergy_id) REFERENCES synergy_opportunities(synergy_id)
            )
            """)
        )
    
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


@pytest.fixture
def client(test_db: AsyncSession):
    """Create test client with database dependency override."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pattern_data():
    """Sample pattern data for testing."""
    return {
        "pattern_type": "time_of_day",
        "device_id": "light.office_lamp",
        "metadata": {
            "time": "07:00",
            "time_range": "06:45-07:15"
        },
        "confidence": 0.85,
        "occurrences": 15
    }


@pytest.fixture
def sample_synergy_data():
    """Sample synergy data for testing."""
    return {
        "synergy_id": "test-synergy-123",
        "synergy_type": "device_pair",
        "devices": ["binary_sensor.motion_office", "light.office_lamp"],
        "opportunity_metadata": {
            "trigger_entity": "binary_sensor.motion_office",
            "action_entity": "light.office_lamp",
            "relationship": "motion_to_light"
        },
        "impact_score": 0.75,
        "complexity": "low",
        "confidence": 0.80,
        "area": "office"
    }


@pytest.fixture
def mock_data_api_client():
    """Mock DataAPIClient for testing."""
    client = AsyncMock()
    
    # Mock fetch_events
    async def mock_fetch_events(*_args, **_kwargs):
        from datetime import datetime, timedelta

        import pandas as pd
        
        # Return sample events DataFrame
        now = datetime.now(UTC)
        events = []
        for i in range(10):
            events.append({
                "timestamp": now - timedelta(hours=i),
                "_time": now - timedelta(hours=i),
                "entity_id": f"light.office_lamp",
                "device_id": f"light.office_lamp",
                "state": "on" if i % 2 == 0 else "off",
                "event_type": "state_changed",
                "domain": "light",
                "friendly_name": "Office Lamp"
            })
        
        return pd.DataFrame(events)
    
    client.fetch_events = mock_fetch_events
    
    # Mock fetch_devices
    async def mock_fetch_devices(*_args, **_kwargs):
        return [
            {
                "device_id": "light.office_lamp",
                "name": "Office Lamp",
                "area_id": "office"
            }
        ]
    
    client.fetch_devices = mock_fetch_devices
    
    # Mock fetch_entities
    async def mock_fetch_entities(*_args, **_kwargs):
        return [
            {
                "entity_id": "light.office_lamp",
                "device_id": "light.office_lamp",
                "domain": "light",
                "area_id": "office"
            }
        ]
    
    client.fetch_entities = mock_fetch_entities
    
    return client


@pytest.fixture
def mock_mqtt_client():
    """Mock MQTTNotificationClient for testing."""
    client = AsyncMock()
    client.publish = AsyncMock(return_value=True)
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock(return_value=True)
    return client

