"""Tests for alerting service."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

from src.alerting_service import (
    AlertSeverity, AlertStatus, AlertRule, Alert, AlertManager,
    EmailNotificationChannel, WebhookNotificationChannel, 
    SlackNotificationChannel, AlertingService
)


class TestAlertRule:
    """Test AlertRule class."""
    
    def test_alert_rule_creation(self):
        """Test alert rule creation."""
        rule = AlertRule(
            name="test_rule",
            description="Test alert rule",
            metric_name="cpu_usage",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )
        
        assert rule.name == "test_rule"
        assert rule.description == "Test alert rule"
        assert rule.metric_name == "cpu_usage"
        assert rule.condition == ">"
        assert rule.threshold == 80.0
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True
        assert rule.cooldown_minutes == 5
        assert rule.notification_channels == []
    
    def test_alert_rule_to_dict(self):
        """Test alert rule to dictionary conversion."""
        rule = AlertRule(
            name="test_rule",
            description="Test alert rule",
            metric_name="cpu_usage",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.WARNING,
            enabled=False,
            cooldown_minutes=10,
            notification_channels=["email", "slack"]
        )
        
        data = rule.to_dict()
        
        assert data["name"] == "test_rule"
        assert data["description"] == "Test alert rule"
        assert data["metric_name"] == "cpu_usage"
        assert data["condition"] == ">"
        assert data["threshold"] == 80.0
        assert data["severity"] == "warning"
        assert data["enabled"] is False
        assert data["cooldown_minutes"] == 10
        assert data["notification_channels"] == ["email", "slack"]


class TestAlert:
    """Test Alert class."""
    
    def test_alert_creation(self):
        """Test alert creation."""
        alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="CPU usage is high",
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z"
        )
        
        assert alert.alert_id == "alert-123"
        assert alert.rule_name == "test_rule"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.message == "CPU usage is high"
        assert alert.metric_name == "cpu_usage"
        assert alert.metric_value == 85.0
        assert alert.threshold == 80.0
        assert alert.condition == ">"
        assert alert.status == AlertStatus.ACTIVE
        assert alert.created_at == "2024-01-01T00:00:00Z"
    
    def test_alert_to_dict(self):
        """Test alert to dictionary conversion."""
        alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="CPU usage is high",
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z",
            acknowledged_at="2024-01-01T01:00:00Z",
            acknowledged_by="admin"
        )
        
        data = alert.to_dict()
        
        assert data["alert_id"] == "alert-123"
        assert data["rule_name"] == "test_rule"
        assert data["severity"] == AlertSeverity.WARNING
        assert data["message"] == "CPU usage is high"
        assert data["metric_name"] == "cpu_usage"
        assert data["metric_value"] == 85.0
        assert data["threshold"] == 80.0
        assert data["condition"] == ">"
        assert data["status"] == AlertStatus.ACTIVE
        assert data["created_at"] == "2024-01-01T00:00:00Z"
        assert data["acknowledged_at"] == "2024-01-01T01:00:00Z"
        assert data["acknowledged_by"] == "admin"


class TestNotificationChannels:
    """Test notification channel classes."""
    
    def test_email_notification_channel_creation(self):
        """Test email notification channel creation."""
        config = {
            "enabled": True,
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "username": "user@example.com",
            "password": "password",
            "from_email": "alerts@example.com",
            "to_emails": ["admin@example.com"],
            "use_tls": True
        }
        
        channel = EmailNotificationChannel("email", config)
        
        assert channel.name == "email"
        assert channel.enabled is True
        assert channel.smtp_server == "smtp.example.com"
        assert channel.smtp_port == 587
        assert channel.username == "user@example.com"
        assert channel.password == "password"
        assert channel.from_email == "alerts@example.com"
        assert channel.to_emails == ["admin@example.com"]
        assert channel.use_tls is True
    
    def test_webhook_notification_channel_creation(self):
        """Test webhook notification channel creation."""
        config = {
            "enabled": True,
            "webhook_url": "https://api.example.com/webhook",
            "headers": {"Authorization": "Bearer token"},
            "timeout": 10
        }
        
        channel = WebhookNotificationChannel("webhook", config)
        
        assert channel.name == "webhook"
        assert channel.enabled is True
        assert channel.webhook_url == "https://api.example.com/webhook"
        assert channel.headers == {"Authorization": "Bearer token"}
        assert channel.timeout == 10
    
    def test_slack_notification_channel_creation(self):
        """Test Slack notification channel creation."""
        config = {
            "enabled": True,
            "webhook_url": "https://hooks.slack.com/webhook",
            "channel": "#alerts",
            "username": "HA-Ingestor",
            "icon_emoji": ":warning:"
        }
        
        channel = SlackNotificationChannel("slack", config)
        
        assert channel.name == "slack"
        assert channel.enabled is True
        assert channel.webhook_url == "https://hooks.slack.com/webhook"
        assert channel.channel == "#alerts"
        assert channel.username == "HA-Ingestor"
        assert channel.icon_emoji == ":warning:"


class TestAlertManager:
    """Test AlertManager class."""
    
    def test_alert_manager_creation(self):
        """Test alert manager creation."""
        manager = AlertManager()
        
        assert len(manager.rules) > 0  # Should have default rules
        assert len(manager.active_alerts) == 0
        assert len(manager.alert_history) == 0
        assert len(manager.notification_channels) == 0
        assert len(manager.cooldown_timers) == 0
        assert not manager.is_evaluating
    
    def test_add_remove_rule(self):
        """Test adding and removing alert rules."""
        manager = AlertManager()
        
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            condition=">",
            threshold=50.0,
            severity=AlertSeverity.WARNING
        )
        
        # Add rule
        manager.add_rule(rule)
        assert "test_rule" in manager.rules
        assert manager.get_rule("test_rule") == rule
        
        # Remove rule
        manager.remove_rule("test_rule")
        assert "test_rule" not in manager.rules
        assert manager.get_rule("test_rule") is None
    
    def test_update_rule(self):
        """Test updating alert rule."""
        manager = AlertManager()
        
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            condition=">",
            threshold=50.0,
            severity=AlertSeverity.WARNING
        )
        
        manager.add_rule(rule)
        
        # Update rule
        updated_rule = AlertRule(
            name="test_rule",
            description="Updated test rule",
            metric_name="test_metric",
            condition=">",
            threshold=75.0,
            severity=AlertSeverity.CRITICAL
        )
        
        manager.update_rule(updated_rule)
        
        stored_rule = manager.get_rule("test_rule")
        assert stored_rule.description == "Updated test rule"
        assert stored_rule.threshold == 75.0
        assert stored_rule.severity == AlertSeverity.CRITICAL
    
    def test_evaluate_condition(self):
        """Test condition evaluation."""
        manager = AlertManager()
        
        # Test greater than
        assert manager._evaluate_condition(85.0, ">", 80.0) is True
        assert manager._evaluate_condition(75.0, ">", 80.0) is False
        
        # Test less than
        assert manager._evaluate_condition(75.0, "<", 80.0) is True
        assert manager._evaluate_condition(85.0, "<", 80.0) is False
        
        # Test equal
        assert manager._evaluate_condition(80.0, "==", 80.0) is True
        assert manager._evaluate_condition(85.0, "==", 80.0) is False
        
        # Test not equal
        assert manager._evaluate_condition(85.0, "!=", 80.0) is True
        assert manager._evaluate_condition(80.0, "!=", 80.0) is False
    
    def test_is_in_cooldown(self):
        """Test cooldown checking."""
        manager = AlertManager()
        
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            condition=">",
            threshold=50.0,
            severity=AlertSeverity.WARNING,
            cooldown_minutes=5
        )
        
        manager.add_rule(rule)
        
        # Not in cooldown initially
        assert not manager._is_in_cooldown("test_rule")
        
        # Set cooldown
        manager._set_cooldown("test_rule")
        assert manager._is_in_cooldown("test_rule")
    
    @pytest.mark.asyncio
    async def test_evaluate_alert(self):
        """Test alert evaluation."""
        manager = AlertManager()
        
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )
        
        manager.add_rule(rule)
        
        # Condition not met - no alert
        alert = await manager.evaluate_alert("test_rule", 75.0)
        assert alert is None
        
        # Condition met - create alert
        alert = await manager.evaluate_alert("test_rule", 85.0)
        assert alert is not None
        assert alert.rule_name == "test_rule"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.metric_value == 85.0
        assert alert.status == AlertStatus.ACTIVE
        
        # Same condition met again - should return existing alert
        alert2 = await manager.evaluate_alert("test_rule", 90.0)
        assert alert2 is not None
        assert alert2.alert_id == alert.alert_id  # Same alert
    
    @pytest.mark.asyncio
    async def test_evaluate_all_alerts(self):
        """Test evaluating all alerts."""
        manager = AlertManager()
        
        # Add test rule
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )
        
        manager.add_rule(rule)
        
        # Evaluate with metrics
        metrics = {
            "test_metric": 85.0,
            "other_metric": 50.0
        }
        
        await manager.evaluate_all_alerts(metrics)
        
        # Should have one active alert
        assert len(manager.active_alerts) == 1
        assert "test_rule" in manager.active_alerts
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        manager = AlertManager()
        
        # Create alert
        alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            metric_name="test_metric",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        manager.active_alerts["test_rule"] = alert
        
        # Acknowledge alert
        success = manager.acknowledge_alert("alert-123", "admin")
        assert success is True
        
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "admin"
        assert alert.acknowledged_at is not None
    
    def test_resolve_alert(self):
        """Test resolving an alert."""
        manager = AlertManager()
        
        # Create alert
        alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            metric_name="test_metric",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        manager.active_alerts["test_rule"] = alert
        
        # Resolve alert
        success = manager.resolve_alert("alert-123", "admin")
        assert success is True
        
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_by == "admin"
        assert alert.resolved_at is not None
        assert "test_rule" not in manager.active_alerts
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        manager = AlertManager()
        
        # Create active alert
        alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            metric_name="test_metric",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        manager.active_alerts["test_rule"] = alert
        
        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].alert_id == "alert-123"
    
    def test_get_alert_history(self):
        """Test getting alert history."""
        manager = AlertManager()
        
        # Add alerts to history
        alert1 = Alert(
            alert_id="alert-1",
            rule_name="rule1",
            severity=AlertSeverity.WARNING,
            message="Alert 1",
            metric_name="metric1",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z"
        )
        
        alert2 = Alert(
            alert_id="alert-2",
            rule_name="rule2",
            severity=AlertSeverity.CRITICAL,
            message="Alert 2",
            metric_name="metric2",
            metric_value=95.0,
            threshold=90.0,
            condition=">",
            status=AlertStatus.RESOLVED,
            created_at="2024-01-01T01:00:00Z"
        )
        
        manager.alert_history = [alert1, alert2]
        
        # Get all history
        history = manager.get_alert_history()
        assert len(history) == 2
        
        # Filter by status
        active_history = manager.get_alert_history(status=AlertStatus.ACTIVE)
        assert len(active_history) == 1
        assert active_history[0].alert_id == "alert-1"
        
        # Filter by severity
        critical_history = manager.get_alert_history(severity=AlertSeverity.CRITICAL)
        assert len(critical_history) == 1
        assert critical_history[0].alert_id == "alert-2"
    
    def test_get_alert_statistics(self):
        """Test getting alert statistics."""
        manager = AlertManager()
        
        # Add some rules and alerts
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )
        manager.add_rule(rule)
        
        alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            metric_name="test_metric",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        manager.active_alerts["test_rule"] = alert
        manager.alert_history.append(alert)
        
        stats = manager.get_alert_statistics()
        
        assert stats["active_alerts_count"] == 1
        assert stats["total_rules"] >= 1  # Including default rules
        assert stats["enabled_rules"] >= 1
        assert "warning" in stats["active_alerts_by_severity"]
        assert "active" in stats["alert_history_by_status"]


class TestAlertingService:
    """Test AlertingService class."""
    
    def test_alerting_service_creation(self):
        """Test alerting service creation."""
        service = AlertingService()
        
        assert isinstance(service.alert_manager, AlertManager)
        assert not service.is_running
    
    def test_get_alert_manager(self):
        """Test getting alert manager."""
        service = AlertingService()
        manager = service.get_alert_manager()
        
        assert manager is service.alert_manager
    
    def test_add_notification_channel(self):
        """Test adding notification channel."""
        service = AlertingService()
        
        config = {
            "enabled": True,
            "webhook_url": "https://api.example.com/webhook"
        }
        
        service.add_notification_channel("test_webhook", "webhook", config)
        
        assert "test_webhook" in service.alert_manager.notification_channels
    
    @pytest.mark.asyncio
    async def test_evaluate_metrics(self):
        """Test evaluating metrics."""
        service = AlertingService()
        
        # Add test rule
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )
        
        service.alert_manager.add_rule(rule)
        
        metrics = {"test_metric": 85.0}
        await service.evaluate_metrics(metrics)
        
        assert len(service.alert_manager.active_alerts) == 1
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        service = AlertingService()
        
        # Add active alert
        alert = Alert(
            alert_id="alert-123",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert",
            metric_name="test_metric",
            metric_value=85.0,
            threshold=80.0,
            condition=">",
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        service.alert_manager.active_alerts["test_rule"] = alert
        
        active_alerts = service.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].alert_id == "alert-123"
    
    def test_get_alert_history(self):
        """Test getting alert history."""
        service = AlertingService()
        
        history = service.get_alert_history(limit=10)
        assert isinstance(history, list)
    
    def test_get_alert_statistics(self):
        """Test getting alert statistics."""
        service = AlertingService()
        
        stats = service.get_alert_statistics()
        
        assert "active_alerts_count" in stats
        assert "total_rules" in stats
        assert "enabled_rules" in stats
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping service."""
        service = AlertingService()
        
        # Start service
        await service.start()
        assert service.is_running
        
        # Stop service
        await service.stop()
        assert not service.is_running
