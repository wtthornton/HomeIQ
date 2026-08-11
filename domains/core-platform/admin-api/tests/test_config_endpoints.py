"""
Tests for configuration endpoints
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.config_endpoints import ConfigEndpoints


class TestConfigEndpoints:
    """Test ConfigEndpoints class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config_endpoints = ConfigEndpoints()
        # Mount the router on a FastAPI app: TestClient(router) skips the
        # app-level middleware that populates fastapi_middleware_astack.
        app = FastAPI()
        app.include_router(self.config_endpoints.router)
        self.client = TestClient(app)

    def test_init(self):
        """Test ConfigEndpoints initialization"""
        assert self.config_endpoints.router is not None
        assert hasattr(self.config_endpoints, "router")
        assert hasattr(self.config_endpoints, "service_urls")

    def test_config_endpoint(self):
        """Test config endpoint"""
        response = self.client.get("/config")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_config_endpoint_with_service(self):
        """A configured service returns its real config, with secrets masked."""
        with patch("src.config_endpoints.config_manager") as mock_cm:
            mock_cm.read_config.return_value = {"HA_URL": "ws://ha:8123", "HA_TOKEN": "secret"}
            mock_cm.sanitize_config.return_value = {"HA_URL": "ws://ha:8123", "HA_TOKEN": "***"}

            response = self.client.get("/config?service=websocket-ingestion")

            assert response.status_code == 200
            data = response.json()["websocket-ingestion"]
            assert data["available"] is True
            assert data["configuration"]["HA_URL"] == "ws://ha:8123"
            # Read through ConfigManager, not fabricated.
            mock_cm.read_config.assert_called_once_with("websocket-ingestion")
            mock_cm.sanitize_config.assert_called_once()

    def test_config_endpoint_with_service_missing_file_is_404(self):
        """An explicitly requested service with no .env file is a 404.

        Regression: this returned 200 with ``configuration: {}``, which reads as
        'this service has no settings' rather than 'nothing was ever read'.
        """
        with patch("src.config_endpoints.config_manager") as mock_cm:
            mock_cm.read_config.side_effect = FileNotFoundError("missing")

            response = self.client.get("/config?service=websocket-ingestion")

            assert response.status_code == 404
            assert "No configuration file" in response.json()["detail"]

    def test_config_endpoint_with_include_sensitive(self):
        """Test config endpoint with include_sensitive parameter"""
        response = self.client.get("/config?include_sensitive=true")

        assert response.status_code == 403
        assert "detail" in response.json()

    def test_config_endpoint_with_invalid_service(self):
        """Test config endpoint with invalid service"""
        response = self.client.get("/config?service=invalid-service")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_config_schema_endpoint(self):
        """Test config schema endpoint"""
        response = self.client.get("/config/schema")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_update_configuration_endpoint(self):
        """A PUT must actually write through ConfigManager.

        Regression: _apply_config_updates echoed the payload back as
        ``status: accepted`` and persisted nothing, so an operator changing
        production config got a 200 and no state change.
        """
        updates = [{"key": "HA_URL", "value": "ws://new:8123", "reason": "Test update"}]

        with patch("src.config_endpoints.config_manager") as mock_cm:
            mock_cm.get_config_template.return_value = {}
            mock_cm.write_config.return_value = {"HA_URL": "ws://new:8123"}
            mock_cm.sanitize_config.return_value = {"HA_URL": "ws://new:8123"}

            response = self.client.put("/config/websocket-ingestion", json=updates)

            assert response.status_code == 200
            assert response.json()["result"]["status"] == "applied"
            mock_cm.write_config.assert_called_once_with(
                "websocket-ingestion", {"HA_URL": "ws://new:8123"}
            )

    def test_update_configuration_rejects_sensitive_key_write(self):
        """A blocked secret write surfaces as 403, not a fake success."""
        updates = [{"key": "HA_TOKEN", "value": "new-secret"}]

        with patch("src.config_endpoints.config_manager") as mock_cm:
            mock_cm.get_config_template.return_value = {}
            mock_cm.write_config.side_effect = PermissionError(
                "Updating sensitive keys via API is disabled: HA_TOKEN"
            )

            response = self.client.put("/config/websocket-ingestion", json=updates)

            assert response.status_code == 403
            assert "HA_TOKEN" in response.json()["detail"]

    def test_update_configuration_endpoint_with_invalid_service(self):
        """Test update configuration endpoint with invalid service"""
        updates = [{"key": "test_key", "value": "test_value", "reason": "Test update"}]

        response = self.client.put("/config/invalid-service", json=updates)

        # Should return 404 for invalid service
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Service invalid-service not found" in data["detail"]

    def test_validate_configuration_endpoint(self):
        """Test validate configuration endpoint"""
        config = {"test_key": "test_value", "another_key": 123}

        response = self.client.post("/config/websocket-ingestion/validate", json=config)

        # Should handle gracefully (may return 500 if service is not available)
        assert response.status_code in [200, 500]

    def test_validate_configuration_endpoint_with_invalid_service(self):
        """Test validate configuration endpoint with invalid service"""
        config = {"test_key": "test_value", "another_key": 123}

        response = self.client.post("/config/invalid-service/validate", json=config)

        # Should return 404 for invalid service
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Service invalid-service not found" in data["detail"]

    def test_backup_configuration_endpoint(self):
        """Backup is 501: there is no configuration archive to read from.

        Regression: this returned 200 with ``backup: {}``, so an operator taking
        a pre-change backup believed they had one.
        """
        response = self.client.get("/config/websocket-ingestion/backup")

        assert response.status_code == 501
        assert "no configuration backup store" in response.json()["detail"]

    def test_backup_configuration_endpoint_with_invalid_service(self):
        """Test backup configuration endpoint with invalid service"""
        response = self.client.get("/config/invalid-service/backup")

        # Should return 404 for invalid service
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Service invalid-service not found" in data["detail"]

    def test_restore_configuration_endpoint(self):
        """Test restore configuration endpoint"""
        backup_data = {
            "service": "websocket-ingestion",
            "timestamp": "2024-01-01T12:00:00Z",
            "backup": {"test_key": "test_value"},
        }

        response = self.client.post("/config/websocket-ingestion/restore", json=backup_data)

        # Regression: this echoed the posted payload back as restored=True while
        # changing nothing -- a rollback that silently did not happen.
        assert response.status_code == 501
        assert "no configuration backup store" in response.json()["detail"]

    def test_restore_configuration_endpoint_with_invalid_service(self):
        """Test restore configuration endpoint with invalid service"""
        backup_data = {
            "service": "invalid-service",
            "timestamp": "2024-01-01T12:00:00Z",
            "backup": {"test_key": "test_value"},
        }

        response = self.client.post("/config/invalid-service/restore", json=backup_data)

        # Should return 404 for invalid service
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Service invalid-service not found" in data["detail"]

    def test_config_history_endpoint(self):
        """History is 501: no change log is recorded anywhere.

        Regression: this fabricated ``limit`` identical empty-change records, so
        an audit of who changed what returned invented rows.
        """
        response = self.client.get("/config/websocket-ingestion/history")

        assert response.status_code == 501
        assert "no configuration change-history store" in response.json()["detail"]

    def test_config_history_endpoint_with_limit(self):
        """The limit parameter does not conjure history either."""
        response = self.client.get("/config/websocket-ingestion/history?limit=5")

        assert response.status_code == 501

    def test_config_history_endpoint_with_invalid_service(self):
        """Test config history endpoint with invalid service"""
        response = self.client.get("/config/invalid-service/history")

        # Should return 404 for invalid service
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Service invalid-service not found" in data["detail"]

    def test_config_endpoint_error_handling(self):
        """Test config endpoint error handling"""
        # Mock the _get_service_config method to raise an exception
        with patch.object(
            self.config_endpoints, "_get_service_config", side_effect=Exception("Test error")
        ):
            response = self.client.get("/config")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get configuration" in data["detail"]

    def test_config_schema_endpoint_error_handling(self):
        """Test config schema endpoint error handling"""
        # Mock the _get_config_schema method to raise an exception
        with patch.object(
            self.config_endpoints, "_get_config_schema", side_effect=Exception("Test error")
        ):
            response = self.client.get("/config/schema")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get configuration schema" in data["detail"]

    def test_update_configuration_endpoint_error_handling(self):
        """Test update configuration endpoint error handling"""
        updates = [{"key": "test_key", "value": "test_value", "reason": "Test update"}]

        # Mock the _apply_config_updates method to raise an exception
        with patch.object(
            self.config_endpoints, "_apply_config_updates", side_effect=Exception("Test error")
        ):
            response = self.client.put("/config/websocket-ingestion", json=updates)

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to update configuration" in data["detail"]

    def test_validate_configuration_endpoint_error_handling(self):
        """Test validate configuration endpoint error handling"""
        config = {"test_key": "test_value", "another_key": 123}

        # Mock the _validate_service_config method to raise an exception
        with patch.object(
            self.config_endpoints, "_validate_service_config", side_effect=Exception("Test error")
        ):
            response = self.client.post("/config/websocket-ingestion/validate", json=config)

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to validate configuration" in data["detail"]

    def test_backup_configuration_endpoint_error_handling(self):
        """Test backup configuration endpoint error handling"""
        # Mock the _backup_service_config method to raise an exception
        with patch.object(
            self.config_endpoints, "_backup_service_config", side_effect=Exception("Test error")
        ):
            response = self.client.get("/config/websocket-ingestion/backup")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to backup configuration" in data["detail"]

    def test_restore_configuration_endpoint_error_handling(self):
        """Test restore configuration endpoint error handling"""
        backup_data = {
            "service": "websocket-ingestion",
            "timestamp": "2024-01-01T12:00:00Z",
            "backup": {"test_key": "test_value"},
        }

        # Mock the _restore_service_config method to raise an exception
        with patch.object(
            self.config_endpoints, "_restore_service_config", side_effect=Exception("Test error")
        ):
            response = self.client.post("/config/websocket-ingestion/restore", json=backup_data)

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to restore configuration" in data["detail"]

    def test_config_history_endpoint_error_handling(self):
        """Test config history endpoint error handling"""
        # Mock the _get_config_history method to raise an exception
        with patch.object(
            self.config_endpoints, "_get_config_history", side_effect=Exception("Test error")
        ):
            response = self.client.get("/config/websocket-ingestion/history")

            # Should handle error gracefully
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to get configuration history" in data["detail"]

    def test_validate_type(self):
        """Test type validation"""
        # Test string type
        assert self.config_endpoints._validate_type("test", "string") is True
        assert self.config_endpoints._validate_type(123, "string") is False

        # Test integer type
        assert self.config_endpoints._validate_type(123, "integer") is True
        assert self.config_endpoints._validate_type("123", "integer") is False

        # Test float type
        assert self.config_endpoints._validate_type(123.45, "float") is True
        assert self.config_endpoints._validate_type(123, "float") is True
        assert self.config_endpoints._validate_type("123.45", "float") is False

        # Test boolean type
        assert self.config_endpoints._validate_type(True, "boolean") is True
        assert self.config_endpoints._validate_type(False, "boolean") is True
        assert self.config_endpoints._validate_type("true", "boolean") is False

        # Test array type
        assert self.config_endpoints._validate_type([1, 2, 3], "array") is True
        assert self.config_endpoints._validate_type("not_array", "array") is False

        # Test object type
        assert self.config_endpoints._validate_type({"key": "value"}, "object") is True
        assert self.config_endpoints._validate_type("not_object", "object") is False

        # Test unknown type
        assert self.config_endpoints._validate_type("anything", "unknown") is True

    def test_validate_rules(self):
        """Test validation rules"""
        # Test min/max validation
        rules = {"min": 10, "max": 100}
        result = self.config_endpoints._validate_rules(50, rules)
        assert result["errors"] == []
        assert result["warnings"] == []

        result = self.config_endpoints._validate_rules(5, rules)
        assert len(result["errors"]) > 0
        assert "below minimum" in result["errors"][0]

        result = self.config_endpoints._validate_rules(150, rules)
        assert len(result["errors"]) > 0
        assert "above maximum" in result["errors"][0]

        # Test string length validation
        rules = {"min_length": 5, "max_length": 10}
        result = self.config_endpoints._validate_rules("test", rules)
        assert len(result["errors"]) > 0
        assert "below minimum" in result["errors"][0]

        result = self.config_endpoints._validate_rules("very_long_string", rules)
        assert len(result["errors"]) > 0
        assert "above maximum" in result["errors"][0]

        result = self.config_endpoints._validate_rules("perfect", rules)
        assert result["errors"] == []
        assert result["warnings"] == []

        # Test pattern validation
        rules = {"pattern": r"^[a-z]+$"}
        result = self.config_endpoints._validate_rules("test", rules)
        assert result["errors"] == []
        assert result["warnings"] == []

        result = self.config_endpoints._validate_rules("Test123", rules)
        assert len(result["errors"]) > 0
        assert "does not match pattern" in result["errors"][0]

        # Test enum validation
        rules = {"enum": ["option1", "option2", "option3"]}
        result = self.config_endpoints._validate_rules("option1", rules)
        assert result["errors"] == []
        assert result["warnings"] == []

        result = self.config_endpoints._validate_rules("invalid_option", rules)
        assert len(result["errors"]) > 0
        assert "not in allowed values" in result["errors"][0]

    def test_config_endpoint_response_time(self):
        """Test config endpoint response time"""
        import time

        start_time = time.time()
        response = self.client.get("/config")
        end_time = time.time()

        assert response.status_code == 200

        # Should respond quickly (less than 1 second)
        response_time = end_time - start_time
        assert response_time < 1.0

    def test_config_endpoint_content_type(self):
        """Test config endpoint content type"""
        response = self.client.get("/config")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_config_endpoint_post_method(self):
        """Test config endpoint with POST method"""
        response = self.client.post("/config")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_config_endpoint_put_method(self):
        """Test config endpoint with PUT method"""
        response = self.client.put("/config")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_config_endpoint_delete_method(self):
        """Test config endpoint with DELETE method"""
        response = self.client.delete("/config")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405
