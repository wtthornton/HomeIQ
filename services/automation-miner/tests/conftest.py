from tests.path_setup import add_service_src

add_service_src(__file__)
"""
Shared pytest fixtures for Automation Miner service tests

Following Context7 KB best practices from /pytest-dev/pytest
"""

import os
from datetime import datetime

import pytest
from httpx import AsyncClient

if not os.getenv("AUTOMATION_MINER_TESTS"):
    pytest.skip(
        "automation-miner tests require external services and env configuration; skipping in alpha environment",
        allow_module_level=True,
    )


# ✅ Context7 Best Practice: Shared async client
@pytest.fixture
async def client():
    """Async HTTP client for Automation Miner API"""
    from src.api.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ✅ Context7 Best Practice: Database fixtures
@pytest.fixture
async def test_db():
    """
    Test database with automatic setup and teardown
    
    Creates tables before test, drops after test completes.
    """
    from src.miner.database import get_database
    
    db = get_database()
    await db.create_tables()
    yield db
    await db.drop_tables()
    await db.close()


@pytest.fixture
async def test_repository(test_db):
    """Test repository with database session"""
    from src.miner.repository import CorpusRepository
    
    async for session in test_db.get_session():
        repo = CorpusRepository(session)
        yield repo
        break


# ✅ Context7 Best Practice: Sample data fixtures
@pytest.fixture
def sample_automation_metadata():
    """Sample automation metadata for testing"""
    from src.miner.models import AutomationMetadata
    
    return AutomationMetadata(
        title="Test Automation",
        description="Test automation for unit tests",
        devices=["light", "motion_sensor"],
        integrations=["mqtt", "homeassistant"],
        triggers=[{"type": "state", "entity_id": "binary_sensor.motion"}],
        conditions=[{"condition": "time", "after": "18:00"}],
        actions=[{"service": "light.turn_on", "entity_id": "light.living_room"}],
        use_case="comfort",
        complexity="low",
        quality_score=0.85,
        vote_count=500,
        source="discourse",
        source_id="test123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


# ✅ Context7 Best Practice: Parametrized search queries
@pytest.fixture(params=[
    {"device": "light", "min_quality": 0.7, "limit": 10},
    {"device": "motion_sensor", "min_quality": 0.8, "limit": 5},
    {"use_case": "security", "min_quality": 0.9, "limit": 20},
])
def search_params(request):
    """Parametrized search query fixtures"""
    return request.param


# ✅ Context7 Best Practice: Test markers
def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "database: Database tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "parser: Parser tests")

