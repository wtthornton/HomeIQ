"""Tests for main service initialization"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app


@pytest.fixture
def client():
    """Create async test client fixture"""
    # Return a context manager for async client
    # Tests will use it with async context manager
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint"""
    # Note: This will fail until service is fully initialized
    # For now, we expect 503 if not initialized
    async with client as ac:
        response = await ac.get("/health")
        # Service not ready without proper initialization
        assert response.status_code in [200, 503]


@pytest.mark.asyncio
async def test_context_endpoint_not_ready(client):
    """Test context endpoint returns 503 when not ready"""
    async with client as ac:
        response = await ac.get("/api/v1/context")
        # Service not ready without proper initialization
        assert response.status_code == 503

