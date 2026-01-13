"""
Tests for metrics endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.utils.metrics import get_metrics, RAGMetrics

client = TestClient(app)


def test_metrics_endpoint():
    """Test metrics endpoint."""
    # Reset metrics for clean test
    metrics = get_metrics()
    metrics.reset()
    
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    
    assert "total_calls" in data
    assert "store_calls" in data
    assert "retrieve_calls" in data
    assert "cache_hits" in data
    assert "cache_misses" in data
    assert "cache_hit_rate" in data
    assert "avg_latency_ms" in data
    assert "errors" in data
    assert "error_rate" in data


def test_stats_endpoint():
    """Test stats endpoint."""
    response = client.get("/api/v1/metrics/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert "total_calls" in data
    assert isinstance(data, dict)
