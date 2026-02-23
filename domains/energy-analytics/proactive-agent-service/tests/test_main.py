"""Tests for main application"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.api.health import set_scheduler_service_for_health


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "proactive-agent-service"
    assert data["version"] == "1.0.0"


def test_health_check_includes_scheduler_status(client):
    """Test health check endpoint includes scheduler status when scheduler is set"""
    # Create a mock scheduler service
    mock_scheduler = MagicMock()
    mock_scheduler.is_running = MagicMock(return_value=True)
    mock_scheduler.get_next_run_time = MagicMock(return_value=datetime(2025, 1, 8, 3, 0, 0))
    
    # Set the scheduler service for health endpoint
    set_scheduler_service_for_health(mock_scheduler)
    
    try:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        assert "scheduler" in data
        assert data["scheduler"]["enabled"] is True
        assert data["scheduler"]["running"] is True
        assert data["scheduler"]["next_run"] is not None
    finally:
        # Clean up - remove scheduler service
        set_scheduler_service_for_health(None)


def test_health_check_scheduler_disabled_when_not_set(client):
    """Test health check endpoint shows scheduler as disabled when not set"""
    # Ensure scheduler service is not set
    set_scheduler_service_for_health(None)
    
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    
    assert "scheduler" in data
    assert data["scheduler"]["enabled"] is False
    assert data["scheduler"]["running"] is False
    assert data["scheduler"]["next_run"] is None

