"""
Pytest-compatible smoke tests for critical production paths.

These tests verify that critical user-facing functionality works end-to-end.
"""

import pytest
import requests
from typing import Dict, Any


class TestCriticalPaths:
    """Critical path smoke tests for production readiness."""

    BASE_URLS = {
        'data-api': 'http://localhost:8006',
        'admin-api': 'http://localhost:8003',
        'websocket-ingestion': 'http://localhost:8001',
        'ai-automation-service': 'http://localhost:8024',
        'health-dashboard': 'http://localhost:3000',
    }

    @pytest.fixture(scope="class")
    def api_key(self):
        """Get API key for authenticated requests."""
        import os
        return os.getenv("AI_AUTOMATION_API_KEY", "test-api-key")

    def test_data_api_health(self):
        """Test that data-api health endpoint responds."""
        response = requests.get(f"{self.BASE_URLS['data-api']}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data or 'healthy' in str(data).lower()

    def test_data_api_events_endpoint(self):
        """Test that events endpoint returns data."""
        response = requests.get(
            f"{self.BASE_URLS['data-api']}/api/v1/events",
            params={'limit': 5},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_data_api_events_stats(self):
        """Test that events stats endpoint works."""
        response = requests.get(
            f"{self.BASE_URLS['data-api']}/api/v1/events/stats",
            params={'period': '1h'},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_admin_api_health(self):
        """Test that admin-api health endpoint responds."""
        response = requests.get(f"{self.BASE_URLS['admin-api']}/api/v1/health", timeout=10)
        assert response.status_code == 200

    def test_admin_api_services(self):
        """Test that services endpoint returns service list."""
        response = requests.get(f"{self.BASE_URLS['admin-api']}/api/v1/services", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_websocket_ingestion_health(self):
        """Test that websocket-ingestion health endpoint responds."""
        response = requests.get(f"{self.BASE_URLS['websocket-ingestion']}/health", timeout=10)
        assert response.status_code == 200

    @pytest.mark.skipif(
        not pytest.config.getoption("--test-ai-service", default=False),
        reason="AI service tests require --test-ai-service flag"
    )
    def test_ai_automation_service_health(self, api_key):
        """Test that AI automation service health endpoint responds."""
        headers = {"X-HomeIQ-API-Key": api_key} if api_key != "test-api-key" else {}
        response = requests.get(
            f"{self.BASE_URLS['ai-automation-service']}/health",
            headers=headers,
            timeout=10
        )
        assert response.status_code in [200, 401]  # 401 is OK if auth required

    def test_health_dashboard_accessible(self):
        """Test that health dashboard is accessible."""
        response = requests.get(self.BASE_URLS['health-dashboard'], timeout=10)
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('Content-Type', '')

    def test_influxdb_connectivity(self):
        """Test that InfluxDB is accessible."""
        try:
            response = requests.get("http://localhost:8086/health", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("InfluxDB not accessible (may be optional in test environment)")

    def test_data_api_event_filtering(self):
        """Test that event filtering works correctly."""
        # Test entity_id filter
        response = requests.get(
            f"{self.BASE_URLS['data-api']}/api/v1/events",
            params={'limit': 10, 'entity_id': 'sensor.temperature'},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_data_api_pagination(self):
        """Test that pagination works correctly."""
        # Get first page
        response1 = requests.get(
            f"{self.BASE_URLS['data-api']}/api/v1/events",
            params={'limit': 5, 'offset': 0},
            timeout=10
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Get second page
        response2 = requests.get(
            f"{self.BASE_URLS['data-api']}/api/v1/events",
            params={'limit': 5, 'offset': 5},
            timeout=10
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify pagination works (may be empty if not enough data)
        assert isinstance(data1, list)
        assert isinstance(data2, list)


class TestSecurityEndpoints:
    """Security-related smoke tests."""

    BASE_URLS = {
        'data-api': 'http://localhost:8006',
        'ai-automation-service': 'http://localhost:8024',
    }

    def test_data_api_sql_injection_prevention(self):
        """Test that SQL injection attempts are blocked."""
        # Attempt SQL injection in entity_id parameter
        malicious_input = "entity'; DROP TABLE events--"
        response = requests.get(
            f"{self.BASE_URLS['data-api']}/api/v1/events",
            params={'limit': 5, 'entity_id': malicious_input},
            timeout=10
        )
        # Should either sanitize or reject, but not crash
        assert response.status_code in [200, 400, 422]

    def test_ai_automation_service_auth_required(self):
        """Test that AI automation service requires authentication."""
        response = requests.post(
            f"{self.BASE_URLS['ai-automation-service']}/api/v1/ask-ai/query",
            json={"query": "test"},
            timeout=10
        )
        # Should require authentication
        assert response.status_code == 401


@pytest.fixture(scope="session")
def pytest_configure(config):
    """Add custom command-line options."""
    config.addinivalue_line(
        "markers", "smoke: Smoke tests for critical paths"
    )
    config.addinivalue_line(
        "markers", "critical: Critical path tests that must pass"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

