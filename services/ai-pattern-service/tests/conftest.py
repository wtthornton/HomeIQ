"""
Pytest configuration and fixtures for AI Pattern Service

Epic 39, Story 39.8: Pattern Service Testing & Validation
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
from fastapi.testclient import TestClient

# Note: Pattern and SynergyOpportunity models are in shared database
# For testing, we'll use mock models or raw SQL
from src.database import get_db
from src.config import settings
from src.main import app


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
    Note: Pattern and SynergyOpportunity tables are in shared database,
    so we'll use raw SQL or mock models for testing.
    """
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    
    # Create basic tables (Pattern and SynergyOpportunity would be in shared DB)
    # For testing, we'll create minimal schema or use mocks
    async with engine.begin() as conn:
        # Create patterns table if needed
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                device_id TEXT NOT NULL,
                pattern_metadata JSON,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                synergy_id TEXT UNIQUE NOT NULL,
                synergy_type TEXT NOT NULL,
                device_ids TEXT NOT NULL,
                opportunity_metadata JSON,
                impact_score REAL NOT NULL,
                complexity TEXT NOT NULL,
                confidence REAL NOT NULL,
                area TEXT,
                explanation JSON,
                context_breakdown JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        )
        # Create synergy_feedback table for RL feedback loop
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS synergy_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    def override_get_db():
        return test_db
    
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
    async def mock_fetch_events(*args, **kwargs):
        import pandas as pd
        from datetime import datetime, timezone, timedelta
        
        # Return sample events DataFrame
        now = datetime.now(timezone.utc)
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
    async def mock_fetch_devices(*args, **kwargs):
        return [
            {
                "device_id": "light.office_lamp",
                "name": "Office Lamp",
                "area_id": "office"
            }
        ]
    
    client.fetch_devices = mock_fetch_devices
    
    # Mock fetch_entities
    async def mock_fetch_entities(*args, **kwargs):
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

