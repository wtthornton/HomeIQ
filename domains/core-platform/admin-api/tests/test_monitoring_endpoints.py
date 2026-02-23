"""Tests for monitoring endpoints."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.auth import AuthManager
from src.monitoring_endpoints import MonitoringEndpoints


@pytest.fixture
def mock_auth_manager():
    """Create mock auth manager."""
    auth_manager = Mock(spec=AuthManager)
    auth_manager.get_current_user = AsyncMock(return_value={"user_id": "test_user"})
    return auth_manager


@pytest.fixture
def monitoring_endpoints(mock_auth_manager):
    """Create monitoring endpoints instance."""
    return MonitoringEndpoints(mock_auth_manager)


@pytest.fixture
def test_app(monitoring_endpoints):
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(monitoring_endpoints.router, prefix="/api/v1/monitoring")
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestMonitoringEndpoints:
    """Test monitoring endpoints."""

    def test_monitoring_endpoints_creation(self, mock_auth_manager):
        """Test monitoring endpoints creation."""
        endpoints = MonitoringEndpoints(mock_auth_manager)

        assert endpoints.auth_manager is mock_auth_manager
        assert endpoints.router is not None

    @patch('src.monitoring_endpoints.logging_service')
    def test_get_logs(self, mock_logging_service, client):
        """Test getting logs endpoint."""
        # Mock logging service response
        mock_logs = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "level": "INFO",
                "service": "test-service",
                "component": "test-component",
                "message": "Test message"
            }
        ]
        mock_logging_service.get_recent_logs.return_value = mock_logs

        response = client.get("/api/v1/monitoring/logs?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "logs" in data["data"]
        assert len(data["data"]["logs"]) == 1
        assert data["data"]["logs"][0]["message"] == "Test message"

    @patch('src.monitoring_endpoints.logging_service')
    def test_get_log_statistics(self, mock_logging_service, client):
        """Test getting log statistics endpoint."""
        # Mock logging service response
        mock_stats = {
            "total_entries": 100,
            "level_counts": {"INFO": 80, "ERROR": 20},
            "service_counts": {"service1": 50, "service2": 50}
        }
        mock_logging_service.get_log_statistics.return_value = mock_stats

        response = client.get("/api/v1/monitoring/logs/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_entries"] == 100
        assert data["data"]["level_counts"]["INFO"] == 80

    @patch('src.monitoring_endpoints.logging_service')
    def test_compress_logs(self, mock_logging_service, client):
        """Test compress logs endpoint."""
        # Mock logging service response
        mock_logging_service.compress_old_logs.return_value = 5

        response = client.post("/api/v1/monitoring/logs/compress")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["compressed_files"] == 5
        assert "Compressed 5 log files" in data["message"]

    @patch('src.monitoring_endpoints.logging_service')
    def test_cleanup_old_logs(self, mock_logging_service, client):
        """Test cleanup old logs endpoint."""
        # Mock logging service response
        mock_logging_service.cleanup_old_compressed_logs.return_value = 3

        response = client.delete("/api/v1/monitoring/logs/cleanup?days_to_keep=30")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted_files"] == 3
        assert data["data"]["days_to_keep"] == 30

    @patch('src.monitoring_endpoints.metrics_service')
    def test_get_metrics(self, mock_metrics_service, client):
        """Test getting metrics endpoint."""
        # Mock metrics service response
        from src.metrics_service import Metric, MetricType, MetricValue

        mock_metric = Metric(
            name="test_metric",
            type=MetricType.GAUGE,
            description="Test metric",
            unit="count",
            values=[MetricValue("2024-01-01T00:00:00Z", 42.5)]
        )
        mock_metrics_service.get_metrics.return_value = [mock_metric]

        response = client.get("/api/v1/monitoring/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "metrics" in data["data"]
        assert len(data["data"]["metrics"]) == 1
        assert data["data"]["metrics"][0]["name"] == "test_metric"

    @patch('src.monitoring_endpoints.metrics_service')
    def test_get_current_metrics(self, mock_metrics_service, client):
        """Test getting current metrics endpoint."""
        # Mock metrics service response
        mock_current_metrics = {
            "cpu_usage": {"value": 75.5, "timestamp": "2024-01-01T00:00:00Z", "unit": "percent"},
            "memory_usage": {"value": 60.2, "timestamp": "2024-01-01T00:00:00Z", "unit": "percent"}
        }
        mock_metrics_service.get_current_metrics.return_value = mock_current_metrics

        response = client.get("/api/v1/monitoring/metrics/current")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["cpu_usage"]["value"] == 75.5
        assert data["data"]["memory_usage"]["value"] == 60.2

    @patch('src.monitoring_endpoints.metrics_service')
    def test_get_metrics_summary(self, mock_metrics_service, client):
        """Test getting metrics summary endpoint."""
        # Mock metrics service response
        mock_summary = {
            "total_metrics": 10,
            "metric_types": {"gauge": 5, "counter": 3, "timer": 2},
            "total_values": 1000
        }
        mock_metrics_service.get_metrics_summary.return_value = mock_summary

        response = client.get("/api/v1/monitoring/metrics/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_metrics"] == 10
        assert data["data"]["metric_types"]["gauge"] == 5

    @patch('src.monitoring_endpoints.alerting_service')
    def test_get_alerts(self, mock_alerting_service, client):
        """Test getting alerts endpoint."""
        # Mock alerting service response
        from src.alerting_service import Alert, AlertSeverity, AlertStatus

        mock_alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z"
        )

        mock_alert_manager = Mock()
        mock_alert_manager.get_alert_history.return_value = [mock_alert]
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        response = client.get("/api/v1/monitoring/alerts?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "alerts" in data["data"]
        assert len(data["data"]["alerts"]) == 1
        assert data["data"]["alerts"][0]["alert_id"] == "alert-123"

    @patch('src.monitoring_endpoints.alerting_service')
    def test_get_active_alerts(self, mock_alerting_service, client):
        """Test getting active alerts endpoint."""
        # Mock alerting service response
        from src.alerting_service import Alert, AlertSeverity, AlertStatus

        mock_alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z"
        )

        mock_alerting_service.get_active_alerts.return_value = [mock_alert]

        response = client.get("/api/v1/monitoring/alerts/active")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "alerts" in data["data"]
        assert len(data["data"]["alerts"]) == 1
        assert data["data"]["alerts"][0]["alert_id"] == "alert-123"

    @patch('src.monitoring_endpoints.alerting_service')
    def test_get_alert_statistics(self, mock_alerting_service, client):
        """Test getting alert statistics endpoint."""
        # Mock alerting service response
        mock_stats = {
            "active_alerts_count": 2,
            "total_rules": 5,
            "enabled_rules": 4,
            "active_alerts_by_severity": {"warning": 1, "critical": 1}
        }

        mock_alert_manager = Mock()
        mock_alert_manager.get_alert_statistics.return_value = mock_stats
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        response = client.get("/api/v1/monitoring/alerts/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["active_alerts_count"] == 2
        assert data["data"]["total_rules"] == 5

    @patch('src.monitoring_endpoints.alerting_service')
    def test_acknowledge_alert(self, mock_alerting_service, client):
        """Test acknowledging alert endpoint."""
        # Mock alerting service response
        mock_alert_manager = Mock()
        mock_alert_manager.acknowledge_alert.return_value = True
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        response = client.post("/api/v1/monitoring/alerts/alert-123/acknowledge")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "acknowledged successfully" in data["message"]

        # Verify the method was called with correct parameters
        mock_alert_manager.acknowledge_alert.assert_called_once_with("alert-123", "test_user")

    @patch('src.monitoring_endpoints.alerting_service')
    def test_acknowledge_alert_not_found(self, mock_alerting_service, client):
        """Test acknowledging non-existent alert."""
        # Mock alerting service response
        mock_alert_manager = Mock()
        mock_alert_manager.acknowledge_alert.return_value = False
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        response = client.post("/api/v1/monitoring/alerts/non-existent/acknowledge")

        assert response.status_code == 404
        data = response.json()
        assert "Alert not found" in data["detail"]

    @patch('src.monitoring_endpoints.alerting_service')
    def test_resolve_alert(self, mock_alerting_service, client):
        """Test resolving alert endpoint."""
        # Mock alerting service response
        mock_alert_manager = Mock()
        mock_alert_manager.resolve_alert.return_value = True
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        response = client.post("/api/v1/monitoring/alerts/alert-123/resolve")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "resolved successfully" in data["message"]

        # Verify the method was called with correct parameters
        mock_alert_manager.resolve_alert.assert_called_once_with("alert-123", "test_user")

    @patch('src.monitoring_endpoints.alerting_service')
    def test_resolve_alert_not_found(self, mock_alerting_service, client):
        """Test resolving non-existent alert."""
        # Mock alerting service response
        mock_alert_manager = Mock()
        mock_alert_manager.resolve_alert.return_value = False
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        response = client.post("/api/v1/monitoring/alerts/non-existent/resolve")

        assert response.status_code == 404
        data = response.json()
        assert "Alert not found" in data["detail"]

    @patch('src.monitoring_endpoints.metrics_service')
    @patch('src.monitoring_endpoints.alerting_service')
    @patch('src.monitoring_endpoints.logging_service')
    def test_get_dashboard_overview(self, mock_logging_service, mock_alerting_service,
                                   mock_metrics_service, client):
        """Test getting dashboard overview endpoint."""
        # Mock service responses
        mock_metrics_service.get_current_metrics.return_value = {
            "cpu_usage": {"value": 75.5, "timestamp": "2024-01-01T00:00:00Z"}
        }
        mock_metrics_service.get_log_statistics.return_value = {
            "total_entries": 100
        }

        from src.alerting_service import Alert, AlertSeverity, AlertStatus
        mock_alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z"
        )

        mock_alerting_service.get_active_alerts.return_value = [mock_alert]
        mock_alerting_service.get_alert_manager.return_value.get_alert_statistics.return_value = {
            "active_alerts_count": 1
        }

        mock_logging_service.get_recent_logs.return_value = [
            {"message": "Test log entry"}
        ]
        mock_logging_service.get_log_statistics.return_value = {
            "total_entries": 100
        }

        mock_logging_service.is_running = True
        mock_metrics_service.is_running = True
        mock_alerting_service.is_running = True

        response = client.get("/api/v1/monitoring/dashboard/overview")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "current_metrics" in data["data"]
        assert "active_alerts" in data["data"]
        assert "recent_logs" in data["data"]
        assert "system_status" in data["data"]

    @patch('src.monitoring_endpoints.alerting_service')
    def test_get_dashboard_health(self, mock_alerting_service, client):
        """Test getting dashboard health endpoint."""
        # Mock service responses
        from src.alerting_service import Alert, AlertSeverity, AlertStatus

        mock_alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.CRITICAL,
            message="Critical alert",
            metric_name="cpu_usage",
            metric_value=95.0,
            threshold=90.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z"
        )

        mock_alerting_service.get_active_alerts.return_value = [mock_alert]

        # Mock service status
        with patch('src.monitoring_endpoints.logging_service') as mock_logging_service, \
             patch('src.monitoring_endpoints.metrics_service') as mock_metrics_service:

            mock_logging_service.is_running = True
            mock_metrics_service.is_running = True
            mock_alerting_service.is_running = True

            response = client.get("/api/v1/monitoring/dashboard/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "overall_healthy" in data["data"]
            assert data["data"]["overall_healthy"] is False  # Should be False due to critical alert
            assert data["data"]["critical_alerts_count"] == 1
            assert data["data"]["active_alerts_count"] == 1

    @patch('src.monitoring_endpoints.alerting_service')
    def test_get_alert_rules(self, mock_alerting_service, client):
        """Test getting alert rules endpoint."""
        # Mock alerting service response
        from src.alerting_service import AlertRule, AlertSeverity

        mock_rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="cpu_usage",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )

        mock_alert_manager = Mock()
        mock_alert_manager.get_all_rules.return_value = [mock_rule]
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        response = client.get("/api/v1/monitoring/config/alert-rules")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "rules" in data["data"]
        assert len(data["data"]["rules"]) == 1
        assert data["data"]["rules"][0]["name"] == "test_rule"

    @patch('src.monitoring_endpoints.alerting_service')
    def test_create_alert_rule(self, mock_alerting_service, client):
        """Test creating alert rule endpoint."""
        # Mock alerting service response
        mock_alert_manager = Mock()
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        rule_data = {
            "name": "new_rule",
            "description": "New test rule",
            "metric_name": "memory_usage",
            "condition": ">",
            "threshold": 85.0,
            "severity": "warning",
            "enabled": True,
            "cooldown_minutes": 5,
            "notification_channels": ["email"]
        }

        response = client.post("/api/v1/monitoring/config/alert-rules", json=rule_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "created successfully" in data["message"]

        # Verify the method was called
        mock_alert_manager.add_rule.assert_called_once()

    @patch('src.monitoring_endpoints.alerting_service')
    def test_update_alert_rule(self, mock_alerting_service, client):
        """Test updating alert rule endpoint."""
        # Mock alerting service response
        mock_alert_manager = Mock()
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        rule_data = {
            "description": "Updated test rule",
            "metric_name": "cpu_usage",
            "condition": ">",
            "threshold": 90.0,
            "severity": "critical",
            "enabled": True,
            "cooldown_minutes": 2,
            "notification_channels": ["slack"]
        }

        response = client.put("/api/v1/monitoring/config/alert-rules/test_rule", json=rule_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "updated successfully" in data["message"]

        # Verify the method was called
        mock_alert_manager.update_rule.assert_called_once()

    @patch('src.monitoring_endpoints.alerting_service')
    def test_delete_alert_rule(self, mock_alerting_service, client):
        """Test deleting alert rule endpoint."""
        # Mock alerting service response
        mock_alert_manager = Mock()
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        response = client.delete("/api/v1/monitoring/config/alert-rules/test_rule")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]

        # Verify the method was called
        mock_alert_manager.remove_rule.assert_called_once_with("test_rule")

    @patch('src.monitoring_endpoints.alerting_service')
    def test_create_notification_channel(self, mock_alerting_service, client):
        """Test creating notification channel endpoint."""
        channel_data = {
            "name": "test_webhook",
            "type": "webhook",
            "config": {
                "enabled": True,
                "webhook_url": "https://api.example.com/webhook"
            }
        }

        response = client.post("/api/v1/monitoring/config/notification-channels", json=channel_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "created successfully" in data["message"]

        # Verify the method was called
        mock_alerting_service.add_notification_channel.assert_called_once_with(
            "test_webhook", "webhook", channel_data["config"]
        )

    @patch('src.monitoring_endpoints.logging_service')
    def test_export_logs_json(self, mock_logging_service, client):
        """Test exporting logs in JSON format."""
        # Mock logging service response
        mock_logs = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "level": "INFO",
                "service": "test-service",
                "message": "Test message"
            }
        ]
        mock_logging_service.get_recent_logs.return_value = mock_logs

        response = client.get("/api/v1/monitoring/export/logs?format=json&limit=100")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["format"] == "json"
        assert len(data["data"]["logs"]) == 1

    @patch('src.monitoring_endpoints.logging_service')
    def test_export_logs_csv(self, mock_logging_service, client):
        """Test exporting logs in CSV format."""
        # Mock logging service response
        mock_logs = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "level": "INFO",
                "service": "test-service",
                "message": "Test message"
            }
        ]
        mock_logging_service.get_recent_logs.return_value = mock_logs

        response = client.get("/api/v1/monitoring/export/logs?format=csv&limit=100")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["format"] == "csv"
        assert "csv_data" in data["data"]
        assert "timestamp,level,service,message" in data["data"]["csv_data"]

    @patch('src.monitoring_endpoints.metrics_service')
    def test_export_metrics_json(self, mock_metrics_service, client):
        """Test exporting metrics in JSON format."""
        # Mock metrics service response
        from src.metrics_service import Metric, MetricType, MetricValue

        mock_metric = Metric(
            name="test_metric",
            type=MetricType.GAUGE,
            description="Test metric",
            unit="count",
            values=[MetricValue("2024-01-01T00:00:00Z", 42.5)]
        )
        mock_metrics_service.get_metrics.return_value = [mock_metric]

        response = client.get("/api/v1/monitoring/export/metrics?format=json")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["format"] == "json"
        assert len(data["data"]["metrics"]) == 1

    @patch('src.monitoring_endpoints.alerting_service')
    def test_export_alerts_json(self, mock_alerting_service, client):
        """Test exporting alerts in JSON format."""
        # Mock alerting service response
        from src.alerting_service import Alert, AlertSeverity, AlertStatus

        mock_alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z"
        )

        mock_alert_manager = Mock()
        mock_alert_manager.get_alert_history.return_value = [mock_alert]
        mock_alerting_service.get_alert_manager.return_value = mock_alert_manager

        response = client.get("/api/v1/monitoring/export/alerts?format=json&limit=100")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["format"] == "json"
        assert len(data["data"]["alerts"]) == 1
