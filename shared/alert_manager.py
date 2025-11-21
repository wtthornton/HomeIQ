"""
Alert Manager
Epic 17.4: Critical Alerting System

Simple, threshold-based alerting without over-engineering.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    service: str
    metric: str | None = None
    current_value: float | None = None
    threshold_value: float | None = None
    created_at: str | None = None
    resolved_at: str | None = None
    acknowledged_at: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {k: v.value if isinstance(v, Enum) else v
                for k, v in asdict(self).items() if v is not None}


@dataclass
class AlertRule:
    """Alert rule definition"""
    name: str
    condition: Callable[[Any], bool]
    severity: AlertSeverity
    message_template: str
    cooldown_seconds: int = 300  # 5 minutes default
    service: str = "system"
    metric: str | None = None

    def __post_init__(self):
        self.last_triggered = 0.0


class AlertManager:
    """Simple alert manager for threshold-based alerting"""

    def __init__(self, service_name: str = "system"):
        """
        Initialize alert manager

        Args:
            service_name: Name of the service
        """
        self.service_name = service_name
        self.alerts: dict[str, Alert] = {}  # alert_id -> Alert
        self.rules: dict[str, AlertRule] = {}  # rule_name -> AlertRule
        self.alert_history: list[Alert] = []
        self.max_history = 100

        # Auto-register default rules
        self._register_default_rules()

    def register_rule(self, rule: AlertRule):
        """
        Register an alert rule

        Args:
            rule: AlertRule to register
        """
        self.rules[rule.name] = rule
        logger.info(f"Registered alert rule: {rule.name} ({rule.severity})")

    def check_condition(self, rule_name: str, value: Any, metadata: dict[str, Any] | None = None) -> Alert | None:
        """
        Check if a condition triggers an alert

        Args:
            rule_name: Name of the rule to check
            value: Value to evaluate
            metadata: Additional metadata for the alert

        Returns:
            Alert if triggered, None otherwise
        """
        if rule_name not in self.rules:
            logger.warning(f"Rule not found: {rule_name}")
            return None

        rule = self.rules[rule_name]

        # Check cooldown
        current_time = time.time()
        if current_time - rule.last_triggered < rule.cooldown_seconds:
            return None

        # Evaluate condition
        try:
            if rule.condition(value):
                rule.last_triggered = current_time

                # Create alert
                alert_id = f"{rule.service}_{rule_name}_{int(current_time)}"
                alert = Alert(
                    id=alert_id,
                    name=rule.name,
                    severity=rule.severity,
                    status=AlertStatus.ACTIVE,
                    message=rule.message_template.format(value=value),
                    service=rule.service,
                    metric=rule.metric,
                    current_value=float(value) if isinstance(value, (int, float)) else None,
                    threshold_value=None,  # Can be set by caller
                    created_at=datetime.utcnow().isoformat() + "Z",
                    metadata=metadata,
                )

                # Store alert
                self.alerts[alert_id] = alert
                self.alert_history.append(alert)

                # Trim history
                if len(self.alert_history) > self.max_history:
                    self.alert_history = self.alert_history[-self.max_history:]

                logger.warning(f"Alert triggered: {alert.name} - {alert.message}")
                return alert

        except Exception as e:
            logger.exception(f"Error evaluating alert rule {rule_name}: {e}")

        return None

    def get_active_alerts(self, severity: AlertSeverity | None = None) -> list[Alert]:
        """
        Get active alerts

        Args:
            severity: Filter by severity (optional)

        Returns:
            List of active alerts
        """
        alerts = [a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        # Sort by created_at (most recent first)
        alerts.sort(key=lambda x: x.created_at or "", reverse=True)

        return alerts

    def get_alert(self, alert_id: str) -> Alert | None:
        """Get specific alert by ID"""
        return self.alerts.get(alert_id)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert

        Args:
            alert_id: Alert ID to acknowledge

        Returns:
            True if successful
        """
        if alert_id not in self.alerts:
            return False

        alert = self.alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow().isoformat() + "Z"

        logger.info(f"Alert acknowledged: {alert.name}")
        return True

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert

        Args:
            alert_id: Alert ID to resolve

        Returns:
            True if successful
        """
        if alert_id not in self.alerts:
            return False

        alert = self.alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow().isoformat() + "Z"

        logger.info(f"Alert resolved: {alert.name}")
        return True

    def clear_resolved_alerts(self, older_than_hours: int = 24):
        """
        Clear resolved alerts older than specified hours

        Args:
            older_than_hours: Hours threshold for cleanup
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        cutoff_str = cutoff_time.isoformat() + "Z"

        to_remove = []
        for alert_id, alert in self.alerts.items():
            if alert.status == AlertStatus.RESOLVED and alert.resolved_at:
                if alert.resolved_at < cutoff_str:
                    to_remove.append(alert_id)

        for alert_id in to_remove:
            del self.alerts[alert_id]

        if to_remove:
            logger.info(f"Cleared {len(to_remove)} resolved alerts")

    def get_alert_summary(self) -> dict[str, Any]:
        """
        Get summary of current alerts

        Returns:
            Dictionary with alert summary
        """
        active_alerts = self.get_active_alerts()

        return {
            "total_active": len(active_alerts),
            "critical": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
            "warning": len([a for a in active_alerts if a.severity == AlertSeverity.WARNING]),
            "info": len([a for a in active_alerts if a.severity == AlertSeverity.INFO]),
            "total_alerts": len(self.alerts),
            "alert_history_count": len(self.alert_history),
        }

    def _register_default_rules(self):
        """Register default alerting rules"""

        # High CPU usage
        self.register_rule(AlertRule(
            name="high_cpu_usage",
            condition=lambda value: value > 80.0,
            severity=AlertSeverity.WARNING,
            message_template="High CPU usage detected: {value}%",
            service=self.service_name,
            metric="cpu_percent",
            cooldown_seconds=300,
        ))

        # Critical CPU usage
        self.register_rule(AlertRule(
            name="critical_cpu_usage",
            condition=lambda value: value > 95.0,
            severity=AlertSeverity.CRITICAL,
            message_template="Critical CPU usage: {value}%",
            service=self.service_name,
            metric="cpu_percent",
            cooldown_seconds=180,
        ))

        # High memory usage
        self.register_rule(AlertRule(
            name="high_memory_usage",
            condition=lambda value: value > 80.0,
            severity=AlertSeverity.WARNING,
            message_template="High memory usage detected: {value}%",
            service=self.service_name,
            metric="memory_percent",
            cooldown_seconds=300,
        ))

        # Critical memory usage
        self.register_rule(AlertRule(
            name="critical_memory_usage",
            condition=lambda value: value > 95.0,
            severity=AlertSeverity.CRITICAL,
            message_template="Critical memory usage: {value}%",
            service=self.service_name,
            metric="memory_percent",
            cooldown_seconds=180,
        ))

        # Service unhealthy
        self.register_rule(AlertRule(
            name="service_unhealthy",
            condition=lambda value: value in {"unhealthy", "critical"},
            severity=AlertSeverity.CRITICAL,
            message_template="Service health is critical: {value}",
            service=self.service_name,
            metric="health_status",
            cooldown_seconds=60,
        ))

        # High error rate
        self.register_rule(AlertRule(
            name="high_error_rate",
            condition=lambda value: value > 10.0,
            severity=AlertSeverity.WARNING,
            message_template="High error rate detected: {value} errors/min",
            service=self.service_name,
            metric="error_rate",
            cooldown_seconds=300,
        ))


# Global alert manager instances
_alert_managers: dict[str, AlertManager] = {}


def get_alert_manager(service_name: str) -> AlertManager:
    """
    Get or create an alert manager for a service

    Args:
        service_name: Name of the service

    Returns:
        AlertManager instance
    """
    if service_name not in _alert_managers:
        _alert_managers[service_name] = AlertManager(service_name)

    return _alert_managers[service_name]

