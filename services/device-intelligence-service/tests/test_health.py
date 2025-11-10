"""
Device Intelligence Service - Health API Tests

Tests for the health API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import time

class TestHealthAPI:
    """Test health API endpoints."""

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data

    def test_health_endpoint(self, client: TestClient):
        """Test health endpoint."""
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_status_endpoint(self, client: TestClient):
        """Test status endpoint."""
        response = client.get("/health/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "port" in data
        assert "host" in data
        assert "environment" in data
        assert "dependencies" in data

    def test_readiness_endpoint(self, client: TestClient):
        """Test readiness endpoint."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_liveness_endpoint(self, client: TestClient):
        """Test liveness endpoint."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_process_time_header(self, client: TestClient):
        """Test that process time header is added."""
        response = client.get("/health/")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0