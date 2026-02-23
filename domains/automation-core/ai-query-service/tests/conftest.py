"""
Pytest configuration and fixtures for AI Query Service

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
    Note: Query service uses shared database models (AskAIQuery, ClarificationSessionDB).
    """
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    
    # Create basic tables for query service (would be in shared DB in production)
    async with engine.begin() as conn:
        # Create ask_ai_queries table (simplified for testing)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ask_ai_queries (
                query_id TEXT PRIMARY KEY,
                original_query TEXT NOT NULL,
                user_id TEXT,
                parsed_intent TEXT,
                extracted_entities JSON,
                suggestions JSON,
                confidence REAL,
                processing_time_ms INTEGER,
                failure_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create clarification_sessions table (simplified for testing)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS clarification_sessions (
                session_id TEXT PRIMARY KEY,
                original_query_id TEXT,
                original_query TEXT,
                user_id TEXT,
                questions JSON,
                ambiguities JSON,
                current_confidence REAL,
                confidence_threshold REAL,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
async def client(test_db: AsyncSession):
    """Create test client with database dependency override."""
    from httpx import AsyncClient, ASGITransport
    
    async def override_get_db():
        return test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_query_request():
    """Sample query request for testing."""
    return {
        "query": "Turn on the lights in the office when motion is detected",
        "user_id": "test_user"
    }


@pytest.fixture
def sample_entities():
    """Sample extracted entities for testing."""
    return [
        {
            "entity_id": "light.office_lamp",
            "name": "Office Lamp",
            "type": "device",
            "domain": "light",
            "confidence": 0.95,
            "role": "action"
        },
        {
            "entity_id": "binary_sensor.motion_office",
            "name": "Office Motion",
            "type": "device",
            "domain": "binary_sensor",
            "confidence": 0.90,
            "role": "trigger"
        },
        {
            "name": "office",
            "type": "area",
            "confidence": 0.85
        }
    ]


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = AsyncMock()
    client.generate_with_unified_prompt = AsyncMock(return_value={
        "suggestions": [
            {
                "description": "Turn on office lights when motion is detected",
                "trigger_summary": "Motion sensor detects movement",
                "action_summary": "Turn on office lights",
                "confidence": 0.85
            }
        ]
    })
    return client


@pytest.fixture
def mock_data_api_client():
    """Mock DataAPIClient for testing."""
    client = AsyncMock()
    
    async def mock_fetch_entities(*args, **kwargs):
        return [
            {
                "entity_id": "light.office_lamp",
                "friendly_name": "Office Lamp",
                "domain": "light",
                "area_id": "office"
            },
            {
                "entity_id": "binary_sensor.motion_office",
                "friendly_name": "Office Motion",
                "domain": "binary_sensor",
                "area_id": "office"
            }
        ]
    
    client.fetch_entities = mock_fetch_entities
    
    async def mock_fetch_devices(*args, **kwargs):
        return [
            {
                "device_id": "office_lamp_device",
                "name": "Office Lamp",
                "area_id": "office"
            }
        ]
    
    client.fetch_devices = mock_fetch_devices
    
    return client


@pytest.fixture
def mock_entity_extractor():
    """Mock entity extractor for testing."""
    extractor = AsyncMock()
    extractor.extract = AsyncMock(return_value=[
        {
            "entity_id": "light.office_lamp",
            "name": "Office Lamp",
            "type": "device",
            "confidence": 0.95
        }
    ])
    return extractor

