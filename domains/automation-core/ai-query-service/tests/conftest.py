"""
Pytest configuration and fixtures for AI Query Service

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.database import get_db
from src.database.models import Base
from src.main import app

# Phase 2: event_loop fixture removed — pytest-asyncio 1.3.0 manages event loops internally

# Any non-empty key passes AuthenticationMiddleware when settings.api_keys is
# empty (the test default). Sending one keeps the auth code path exercised.
TEST_API_KEY = "test-api-key"


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session with the real ORM schema.

    Defaults to in-memory SQLite so the suite has no external infrastructure
    dependency; set TEST_DATABASE_URL (e.g. postgresql+asyncpg://...) for
    integration runs against a real server. Tables come from
    ``Base.metadata`` — the actual AskAIQuery / ClarificationSession models —
    so the schema can never drift from src the way hand-written DDL did.
    """
    test_url = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite://")
    engine_kwargs: dict = {"echo": False}
    if test_url.startswith("sqlite"):
        # One shared in-memory database across all pooled connections.
        engine_kwargs["poolclass"] = StaticPool
    engine = create_async_engine(
        test_url,
        # Models live in the "automation" schema; map it to the default schema
        # so SQLite (no schemas) works and PostgreSQL needs no CREATE SCHEMA.
        execution_options={"schema_translate_map": {"automation": None}},
        **engine_kwargs,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session

    # Drop tables so a persistent TEST_DATABASE_URL backend stays isolated
    # between tests (no-op cost for the throwaway in-memory default).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(test_db: AsyncSession):
    """Create test client with database dependency override."""
    from httpx import ASGITransport, AsyncClient

    async def override_get_db():
        return test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-HomeIQ-API-Key": TEST_API_KEY},
    ) as ac:
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

    async def mock_fetch_entities(*_args, **_kwargs):
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

    async def mock_fetch_devices(*_args, **_kwargs):
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

