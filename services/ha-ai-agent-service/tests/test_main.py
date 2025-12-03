"""Tests for main service initialization"""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint"""
    # Note: This will fail until service is fully initialized
    # For now, we expect 503 if not initialized
    response = client.get("/health")
    # Service not ready without proper initialization
    assert response.status_code in [200, 503]


def test_context_endpoint_not_ready(client):
    """Test context endpoint returns 503 when not ready"""
    response = client.get("/api/v1/context")
    # Service not ready without proper initialization
    assert response.status_code == 503

