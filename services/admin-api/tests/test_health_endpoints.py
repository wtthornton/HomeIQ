"""
Tests for health endpoints
"""

from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from src.health_endpoints import HealthEndpoints


class TestHealthEndpoints:
    """Test HealthEndpoints class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.health_endpoints = HealthEndpoints()
        self.client = TestClient(self.health_endpoints.router)

    def test_init(self):
        """Test HealthEndpoints initialization"""
        assert self.health_endpoints.router is not None
        assert hasattr(self.health_endpoints, 'router')

    def test_health_endpoint(self):
        """Test health endpoint"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "admin_api_status" in data
        assert "ingestion_service" in data
        assert "timestamp" in data

    def test_health_endpoint_structure(self):
        """Test health endpoint response structure"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "overall_status" in data
        assert "admin_api_status" in data
        assert "ingestion_service" in data
        assert "timestamp" in data

        # Check ingestion service structure
        ingestion_service = data["ingestion_service"]
        assert "status" in ingestion_service
        assert "websocket_connection" in ingestion_service
        assert "event_processing" in ingestion_service
        assert "weather_enrichment" in ingestion_service
        assert "influxdb_storage" in ingestion_service
        assert "timestamp" in ingestion_service

    def test_health_endpoint_status_values(self):
        """Test health endpoint status values"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check status values
        assert data["overall_status"] in ["healthy", "degraded", "unhealthy"]
        assert data["admin_api_status"] == "running"

        # Check ingestion service status
        ingestion_service = data["ingestion_service"]
        assert ingestion_service["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_endpoint_timestamp(self):
        """Test health endpoint timestamp"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check timestamp format
        timestamp = data["timestamp"]
        assert isinstance(timestamp, str)

        # Try to parse timestamp
        parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert isinstance(parsed_timestamp, datetime)

    def test_health_endpoint_ingestion_service_timestamp(self):
        """Test health endpoint ingestion service timestamp"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check ingestion service timestamp
        ingestion_service = data["ingestion_service"]
        timestamp = ingestion_service["timestamp"]
        assert isinstance(timestamp, str)

        # Try to parse timestamp
        parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert isinstance(parsed_timestamp, datetime)

    def test_health_endpoint_websocket_connection(self):
        """Test health endpoint websocket connection data"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check websocket connection data
        websocket_connection = data["ingestion_service"]["websocket_connection"]
        assert "is_connected" in websocket_connection
        assert "last_connection_time" in websocket_connection
        assert "connection_attempts" in websocket_connection
        assert "last_error" in websocket_connection

        # Check data types
        assert isinstance(websocket_connection["is_connected"], bool)
        assert isinstance(websocket_connection["connection_attempts"], int)
        assert websocket_connection["last_error"] is None or isinstance(websocket_connection["last_error"], str)

    def test_health_endpoint_event_processing(self):
        """Test health endpoint event processing data"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check event processing data
        event_processing = data["ingestion_service"]["event_processing"]
        assert "total_events" in event_processing
        assert "events_per_minute" in event_processing
        assert "error_rate" in event_processing

        # Check data types
        assert isinstance(event_processing["total_events"], int)
        assert isinstance(event_processing["events_per_minute"], (int, float))
        assert isinstance(event_processing["error_rate"], (int, float))

    def test_health_endpoint_weather_enrichment(self):
        """Test health endpoint weather enrichment data"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check weather enrichment data
        weather_enrichment = data["ingestion_service"]["weather_enrichment"]
        assert "enabled" in weather_enrichment
        assert "cache_hits" in weather_enrichment
        assert "api_calls" in weather_enrichment
        assert "last_error" in weather_enrichment

        # Check data types
        assert isinstance(weather_enrichment["enabled"], bool)
        assert isinstance(weather_enrichment["cache_hits"], int)
        assert isinstance(weather_enrichment["api_calls"], int)
        assert weather_enrichment["last_error"] is None or isinstance(weather_enrichment["last_error"], str)

    def test_health_endpoint_influxdb_storage(self):
        """Test health endpoint InfluxDB storage data"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check InfluxDB storage data
        influxdb_storage = data["ingestion_service"]["influxdb_storage"]
        assert "is_connected" in influxdb_storage
        assert "last_write_time" in influxdb_storage
        assert "write_errors" in influxdb_storage

        # Check data types
        assert isinstance(influxdb_storage["is_connected"], bool)
        assert isinstance(influxdb_storage["write_errors"], int)
        assert influxdb_storage["last_write_time"] is None or isinstance(influxdb_storage["last_write_time"], str)

    def test_health_endpoint_error_handling(self):
        """Test health endpoint error handling"""
        # Mock the get_ingestion_service_health function to raise an exception
        with patch.object(self.health_endpoints, '_get_ingestion_service_health', side_effect=Exception("Test error")):
            response = self.client.get("/health")

            # Should handle error gracefully
            assert response.status_code == 200
            data = response.json()

            # Should still return basic structure
            assert "overall_status" in data
            assert "admin_api_status" in data
            assert "timestamp" in data

    def test_health_endpoint_degraded_status(self):
        """Test health endpoint degraded status"""
        # Mock the get_ingestion_service_health function to return degraded status
        with patch.object(self.health_endpoints, '_get_ingestion_service_health', return_value={
            "status": "degraded",
            "websocket_connection": {"is_connected": True, "last_connection_time": "2024-01-01T12:00:00Z", "connection_attempts": 5, "last_error": None},
            "event_processing": {"total_events": 1000, "events_per_minute": 50, "error_rate": 0.01},
            "weather_enrichment": {"enabled": True, "cache_hits": 100, "api_calls": 10, "last_error": None},
            "influxdb_storage": {"is_connected": True, "last_write_time": "2024-01-01T12:00:00Z", "write_errors": 0},
            "timestamp": "2024-01-01T12:00:00Z"
        }):
            response = self.client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Should reflect degraded status
            assert data["overall_status"] == "degraded"
            assert data["ingestion_service"]["status"] == "degraded"

    def test_health_endpoint_unhealthy_status(self):
        """Test health endpoint unhealthy status"""
        # Mock the get_ingestion_service_health function to return unhealthy status
        with patch.object(self.health_endpoints, '_get_ingestion_service_health', return_value={
            "status": "unhealthy",
            "websocket_connection": {"is_connected": False, "last_connection_time": "2024-01-01T12:00:00Z", "connection_attempts": 5, "last_error": "Connection failed"},
            "event_processing": {"total_events": 1000, "events_per_minute": 0, "error_rate": 0.5},
            "weather_enrichment": {"enabled": True, "cache_hits": 100, "api_calls": 10, "last_error": "API error"},
            "influxdb_storage": {"is_connected": False, "last_write_time": "2024-01-01T12:00:00Z", "write_errors": 100},
            "timestamp": "2024-01-01T12:00:00Z"
        }):
            response = self.client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Should reflect unhealthy status
            assert data["overall_status"] == "degraded"  # Should be degraded, not unhealthy
            assert data["ingestion_service"]["status"] == "unhealthy"

    def test_health_endpoint_mock_data(self):
        """Test health endpoint with mock data"""
        # Test that the endpoint returns consistent mock data
        response1 = self.client.get("/health")
        response2 = self.client.get("/health")

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Check that structure is consistent
        assert data1.keys() == data2.keys()
        assert data1["ingestion_service"].keys() == data2["ingestion_service"].keys()

        # Check that timestamps are different (should be updated)
        assert data1["timestamp"] != data2["timestamp"]
        assert data1["ingestion_service"]["timestamp"] != data2["ingestion_service"]["timestamp"]

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
