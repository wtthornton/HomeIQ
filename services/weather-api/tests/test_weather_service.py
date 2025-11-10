"""
Tests for Weather Service
Epic 31, Stories 31.2-31.3
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app


client = TestClient(app)


def test_current_weather_endpoint_exists():
    """Test that current weather endpoint is accessible"""
    # Note: Will return 503 without valid API key, but endpoint exists
    response = client.get("/current-weather")
    # Either 200 (if key configured) or 503 (no data)
    assert response.status_code in [200, 503]


def test_cache_stats_endpoint():
    """Test cache statistics endpoint"""
    response = client.get("/cache/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert "hits" in data
    assert "misses" in data
    assert "hit_rate" in data
    assert "ttl_seconds" in data


def test_service_root():
    """Test root endpoint lists weather endpoints"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "/current-weather" in data["endpoints"]
    assert "/cache/stats" in data["endpoints"]

