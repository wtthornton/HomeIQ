"""
Integration Tests for API

Tests FastAPI endpoints.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime

from src.api.main import app
from src.miner.database import get_database
from src.miner.repository import CorpusRepository
from src.miner.models import AutomationMetadata


@pytest.fixture
async def test_db():
    """Create test database"""
    db = get_database()
    await db.create_tables()
    yield db
    await db.drop_tables()
    await db.close()


@pytest.fixture
async def sample_automation(test_db):
    """Create sample automation in database"""
    async for session in test_db.get_session().__aiter__():
        repo = CorpusRepository(session)
        
        metadata = AutomationMetadata(
            title="Test Automation",
            description="Test description",
            devices=["light", "motion_sensor"],
            integrations=["mqtt"],
            triggers=[{"type": "state"}],
            conditions=[],
            actions=[{"service": "light.turn_on"}],
            use_case="comfort",
            complexity="low",
            quality_score=0.85,
            vote_count=500,
            source="discourse",
            source_id="test123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await repo.save_automation(metadata)
        break


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] in ['healthy', 'unhealthy']
        assert data['service'] == 'automation-miner'


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert 'message' in data
        assert 'version' in data


@pytest.mark.asyncio
async def test_search_endpoint(sample_automation):
    """Test search endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/automation-miner/corpus/search",
            params={"device": "light", "min_quality": 0.7, "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'automations' in data
        assert 'count' in data
        assert data['count'] >= 0


@pytest.mark.asyncio
async def test_stats_endpoint(sample_automation):
    """Test stats endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/automation-miner/corpus/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert 'total' in data
        assert 'avg_quality' in data
        assert 'device_count' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

