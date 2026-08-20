"""Tests for automation-trace-service FastAPI endpoints."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create a test client with mocked global state."""
    from src.main import app

    return TestClient(app)


class TestRootEndpoint:
    """Tests for the / root endpoint."""

    def test_root_returns_service_info(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Automation Trace Service"
        assert "version" in data
        assert data["status"] == "running"


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_details_returns_503_when_not_initialized(self, client: TestClient) -> None:
        """Health details returns 503 when trace_poller is not yet initialized."""
        import src.main as main_module

        original = main_module.trace_poller
        main_module.trace_poller = None
        try:
            response = client.get("/health/details")
            assert response.status_code == 503
        finally:
            main_module.trace_poller = original

    def test_health_returns_200_when_healthy(self, client: TestClient) -> None:
        """Health returns 200 with valid poller/writer/client state."""
        import src.main as main_module

        mock_poller = MagicMock()
        mock_poller.poll_count = 10
        mock_poller.traces_captured = 5
        mock_poller.automations_found = 3
        mock_poller.errors = 0
        mock_poller.last_poll = None

        mock_ha = MagicMock()
        mock_ha.is_connected = True

        mock_influx = MagicMock()
        mock_influx.client = MagicMock()

        mock_dedup = MagicMock()
        mock_dedup.tracked_automation_count = 2
        mock_dedup.total_tracked_runs = 10
        mock_dedup.total_deduped = 1

        mock_health = MagicMock()
        mock_health.build.return_value = {"status": "healthy", "services": {}}

        orig_poller = main_module.trace_poller
        orig_ha = main_module.ha_client
        orig_influx = main_module.influxdb_writer
        orig_dedup = main_module.dedup
        orig_health = main_module.health_handler

        main_module.trace_poller = mock_poller
        main_module.ha_client = mock_ha
        main_module.influxdb_writer = mock_influx
        main_module.dedup = mock_dedup
        main_module.health_handler = mock_health
        try:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        finally:
            main_module.trace_poller = orig_poller
            main_module.ha_client = orig_ha
            main_module.influxdb_writer = orig_influx
            main_module.dedup = orig_dedup
            main_module.health_handler = orig_health


class TestMetricsEndpoint:
    """Tests for the /metrics endpoint.

    /metrics is the Prometheus text endpoint registered by create_app(). The
    service used to define a second, JSON /metrics after it — dead code, since
    Starlette matches the first-registered route — and these tests asserted
    that unreachable contract (TAP-6178: the real defect behind the failures;
    the ticket's health-503 premise did not reproduce).
    """

    def test_metrics_serves_prometheus_text(self, client: TestClient) -> None:
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "# HELP" in response.text

    def test_metrics_never_requires_service_initialization(self, client: TestClient) -> None:
        """Prometheus scrapes must work even before the poller starts."""
        import src.main as main_module

        original = main_module.trace_poller
        main_module.trace_poller = None
        try:
            response = client.get("/metrics")
            assert response.status_code == 200
        finally:
            main_module.trace_poller = original
