"""
Pytest configuration and fixtures for AI Automation Service

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from sqlalchemy import text

# Note: These imports will be available once main.py and routers are created
# from src.database import get_db
# from src.config import settings
# from src.main import app


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
    Note: Automation service uses shared database models (Suggestion, etc.).
    """
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    
    # Create basic tables for automation service (would be in shared DB in production)
    async with engine.begin() as conn:
        # Create suggestions table (simplified for testing)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                automation_yaml TEXT,
                confidence REAL,
                category TEXT,
                priority TEXT,
                status TEXT DEFAULT 'draft',
                device_id TEXT,
                devices_involved JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deployed_at TIMESTAMP
            )
        """))
        
        # Create automation_versions table for rollback testing
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS automation_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                automation_id TEXT NOT NULL,
                yaml_content TEXT NOT NULL,
                safety_score REAL,
                deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    
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
def sample_suggestion_data():
    """Sample suggestion data for testing."""
    return {
        "title": "Turn on office lights at 7 AM",
        "description": "Automatically turn on office lights at 7 AM every day",
        "automation_yaml": None,
        "confidence": 0.85,
        "category": "convenience",
        "priority": "medium",
        "status": "draft",
        "device_id": "light.office_lamp",
        "devices_involved": ["light.office_lamp"]
    }


@pytest.fixture
def sample_yaml_content():
    """Sample YAML content for testing."""
    return """id: 'test-automation-123'
alias: Test Automation
description: "Turn on office lights at 7 AM"
mode: single
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
    data:
      brightness_pct: 100
"""


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client for testing."""
    client = AsyncMock()
    client.create_automation = AsyncMock(return_value={
        "success": True,
        "automation_id": "automation.test_automation_123"
    })
    client.list_automations = AsyncMock(return_value=[])
    client.get_automation = AsyncMock(return_value={
        "id": "automation.test",
        "alias": "Test Automation",
        "state": "on"
    })
    client.enable_automation = AsyncMock(return_value=True)
    client.disable_automation = AsyncMock(return_value=True)
    client.trigger_automation = AsyncMock(return_value=True)
    client.test_connection = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for YAML generation testing."""
    client = AsyncMock()
    client.generate_with_unified_prompt = AsyncMock(return_value={
        "automation_yaml": """id: 'test-123'
alias: Test Automation
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
"""
    })
    return client


# Note: client fixture will be added once main.py is created
# @pytest.fixture
# def client(test_db: AsyncSession):
#     """Create test client with database dependency override."""
#     def override_get_db():
#         return test_db
#     
#     app.dependency_overrides[get_db] = override_get_db
#     yield TestClient(app)
#     app.dependency_overrides.clear()

