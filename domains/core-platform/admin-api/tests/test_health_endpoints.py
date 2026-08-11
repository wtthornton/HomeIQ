"""
Tests for health endpoints
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.health_endpoints import HealthEndpoints


class TestHealthEndpoints:
    """Test HealthEndpoints class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.health_endpoints = HealthEndpoints()
        # Mount the router on a FastAPI app: TestClient(router) skips the
        # app-level middleware that populates fastapi_middleware_astack.
        app = FastAPI()
        app.include_router(self.health_endpoints.router)
        self.client = TestClient(app)

    def test_init(self):
        """Test HealthEndpoints initialization"""
        assert self.health_endpoints.router is not None
        assert hasattr(self.health_endpoints, "router")

    def test_health_endpoint(self):
        """Test health endpoint returns the standardized envelope"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "admin-api"
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "version" in data
        assert "dependencies" in data
        assert "metrics" in data

    def test_health_endpoint_structure(self):
        """Test health endpoint response structure"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Every dependency carries the standard descriptor fields
        assert isinstance(data["dependencies"], list)
        assert data["dependencies"], "expected at least one dependency"
        for dependency in data["dependencies"]:
            assert "name" in dependency
            assert "type" in dependency
            assert "status" in dependency
            assert "response_time_ms" in dependency

        metrics = data["metrics"]
        assert "uptime_seconds" in metrics
        assert "uptime_human" in metrics
        assert "uptime_percentage" in metrics
        assert "start_time" in metrics
        assert "current_time" in metrics

    def test_health_endpoint_reports_known_dependencies(self):
        """InfluxDB and the ingestion service are both reported"""
        response = self.client.get("/health")

        names = {d["name"] for d in response.json()["dependencies"]}
        assert "InfluxDB" in names
        assert "WebSocket Ingestion" in names

    def test_health_endpoint_status_values(self):
        """Test health endpoint status values"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        allowed = {"healthy", "degraded", "unhealthy", "critical", "unknown"}
        assert data["status"] in allowed
        for dependency in data["dependencies"]:
            assert dependency["status"] in allowed

    def test_health_endpoint_timestamp(self):
        """Test health endpoint timestamp advances between calls"""
        first = self.client.get("/health").json()
        second = self.client.get("/health").json()

        assert first["timestamp"] != second["timestamp"]
        assert second["uptime_seconds"] >= first["uptime_seconds"]

    def test_health_endpoint_healthy_when_dependencies_pass(self):
        """All dependencies reachable -> healthy overall"""
        with (
            patch.object(self.health_endpoints, "_check_influxdb_health", return_value=True),
            patch.object(self.health_endpoints, "_check_service_health", return_value=True),
        ):
            data = self.client.get("/health").json()

        assert data["status"] == "healthy"
        assert all(d["status"] == "healthy" for d in data["dependencies"])

    def test_health_endpoint_degrades_when_a_dependency_fails(self):
        """A single failing dependency is reflected in the overall status"""
        with (
            patch.object(self.health_endpoints, "_check_influxdb_health", return_value=True),
            patch.object(self.health_endpoints, "_check_service_health", return_value=False),
        ):
            data = self.client.get("/health").json()

        assert data["status"] != "healthy"
        by_name = {d["name"]: d for d in data["dependencies"]}
        assert by_name["InfluxDB"]["status"] == "healthy"
        assert by_name["WebSocket Ingestion"]["status"] != "healthy"

    def test_health_endpoint_error_handling(self):
        """A raising dependency check is contained, not propagated as a 500"""
        with patch.object(
            self.health_endpoints, "_check_influxdb_health", side_effect=Exception("Test error")
        ):
            response = self.client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "admin-api"
            assert data["status"] != "healthy"
            assert "timestamp" in data

    def test_health_endpoint_shape_is_stable_across_calls(self):
        """Repeated calls return the same keys"""
        first = self.client.get("/health").json()
        second = self.client.get("/health").json()

        assert first.keys() == second.keys()
        assert first["metrics"].keys() == second["metrics"].keys()
        assert [d["name"] for d in first["dependencies"]] == [
            d["name"] for d in second["dependencies"]
        ]

    def test_health_endpoint_response_time(self):
        """Test health endpoint response time"""
        import time

        start_time = time.time()
        response = self.client.get("/health")
        end_time = time.time()

        assert response.status_code == 200

        # Should respond quickly (less than 1 second)
        response_time = end_time - start_time
        assert response_time < 1.0

    def test_health_endpoint_content_type(self):
        """Test health endpoint content type"""
        response = self.client.get("/health")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_health_endpoint_cors_headers(self):
        """Test health endpoint CORS headers"""
        response = self.client.options("/health")

        # Should handle OPTIONS request
        assert response.status_code in [200, 405]  # 405 if OPTIONS not supported

    def test_health_endpoint_post_method(self):
        """Test health endpoint with POST method"""
        response = self.client.post("/health")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_health_endpoint_put_method(self):
        """Test health endpoint with PUT method"""
        response = self.client.put("/health")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_health_endpoint_delete_method(self):
        """Test health endpoint with DELETE method"""
        response = self.client.delete("/health")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405
