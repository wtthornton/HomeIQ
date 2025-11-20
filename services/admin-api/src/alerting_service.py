"""
Lightweight alerting service primitives used by admin-api tests.

The implementation focuses on in-memory data structures so unit tests can
exercise rule management and alert lifecycle flows without external services.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class AlertRule:
    name: str
    description: str
    metric_name: str
    condition: str
    threshold: float
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 5
    notification_channels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "metric_name": self.metric_name,
            "condition": self.condition,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "cooldown_minutes": self.cooldown_minutes,
            "notification_channels": list(self.notification_channels),
        }


@dataclass
class Alert:
    alert_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    condition: str
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acknowledged_at: str | None = None
    acknowledged_by: str | None = None
    resolved_at: str | None = None
    resolved_by: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "alert_id": self.alert_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "message": self.message,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "condition": self.condition,
            "status": self.status,
            "created_at": self.created_at,
            "acknowledged_at": self.acknowledged_at,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
        }


class EmailNotificationChannel:
    def __init__(self, name: str, config: dict[str, object]):
        self.name = name
        self.enabled = bool(config.get("enabled", False))
        self.smtp_server = config.get("smtp_server")
        self.smtp_port = config.get("smtp_port")
        self.username = config.get("username")
        self.password = config.get("password")
        self.from_email = config.get("from_email")
        self.to_emails = list(config.get("to_emails", []))
        self.use_tls = bool(config.get("use_tls", False))


class WebhookNotificationChannel:
    def __init__(self, name: str, config: dict[str, object]):
        self.name = name
        self.enabled = bool(config.get("enabled", False))
        self.webhook_url = config.get("webhook_url")
        self.headers = dict(config.get("headers", {}))
        self.timeout = config.get("timeout", 10)


class SlackNotificationChannel:
    def __init__(self, name: str, config: dict[str, object]):
        self.name = name
        self.enabled = bool(config.get("enabled", False))
        self.webhook_url = config.get("webhook_url")
        self.channel = config.get("channel")
        self.username = config.get("username")
        self.icon_emoji = config.get("icon_emoji")


class AlertManager:
    def __init__(self) -> None:
        self.rules: dict[str, AlertRule] = {}
        self.active_alerts: dict[str, Alert] = {}
        self.alert_history: list[Alert] = []
        self.notification_channels: dict[str, object] = {}
        self.cooldown_timers: dict[str, datetime] = {}
        self.is_evaluating: bool = False
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        default_rule = AlertRule(
            name="default_cpu",
            description="CPU usage exceeds threshold",
            metric_name="cpu_usage",
            condition=">",
            threshold=85.0,
            severity=AlertSeverity.WARNING,
        )
        self.rules[default_rule.name] = default_rule

    def add_rule(self, rule: AlertRule) -> None:
        self.rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        self.rules.pop(name, None)

    def get_rule(self, name: str) -> AlertRule | None:
        return self.rules.get(name)

    def update_rule(self, rule: AlertRule) -> None:
        if rule.name not in self.rules:
            raise ValueError(f"Rule '{rule.name}' does not exist.")
        self.rules[rule.name] = rule

    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        if operator == ">":
            return value > threshold
        if operator == "<":
            return value < threshold
        if operator == "==":
            return value == threshold
        if operator == "!=":
            return value != threshold
        return False

    def _is_in_cooldown(self, rule_name: str) -> bool:
        expires_at = self.cooldown_timers.get(rule_name)
        if not expires_at:
            return False
        return expires_at > datetime.now(timezone.utc)

    def _set_cooldown(self, rule_name: str, minutes: int = 5) -> None:
        self.cooldown_timers[rule_name] = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    async def evaluate_alert(self, rule_name: str, metric_value: float) -> Alert | None:
        rule = self.rules.get(rule_name)
        if not rule or not rule.enabled:
            return None

        if self._is_in_cooldown(rule_name):
            return self.active_alerts.get(rule_name)

        if not self._evaluate_condition(metric_value, rule.condition, rule.threshold):
            return None

        existing = self.active_alerts.get(rule_name)
        if existing:
            existing.metric_value = metric_value
            return existing

        alert_id = f"alert-{uuid.uuid4().hex[:8]}"
        message = f"{rule.metric_name} {rule.condition} {rule.threshold}"
        alert = Alert(
            alert_id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            message=message,
            metric_name=rule.metric_name,
            metric_value=metric_value,
            threshold=rule.threshold,
            condition=rule.condition,
        )
        self.active_alerts[rule.name] = alert
        self.alert_history.append(alert)
        self._set_cooldown(rule.name, rule.cooldown_minutes)
        return alert

    async def evaluate_all_alerts(self, metrics: dict[str, float]) -> None:
        if self.is_evaluating:
            return
        self.is_evaluating = True
        try:
            evaluation_tasks = []
            for rule in self.rules.values():
                if rule.metric_name in metrics:
                    value = metrics[rule.metric_name]
                    evaluation_tasks.append(self.evaluate_alert(rule.name, value))
            if evaluation_tasks:
                await asyncio.gather(*evaluation_tasks)
        finally:
            self.is_evaluating = False

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        for alert in self.active_alerts.values():
            if alert.alert_id == alert_id and alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = user
                alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    def resolve_alert(self, alert_id: str, user: str) -> bool:
        for rule_name, alert in list(self.active_alerts.items()):
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_by = user
                alert.resolved_at = datetime.now(timezone.utc).isoformat()
                self.active_alerts.pop(rule_name, None)
                return True
        return False

    def get_active_alerts(self) -> list[Alert]:
        return list(self.active_alerts.values())

    def get_alert_history(
        self,
        *,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        limit: int | None = None,
    ) -> list[Alert]:
        history = self.alert_history
        if status:
            history = [item for item in history if item.status == status]
        if severity:
            history = [item for item in history if item.severity == severity]
        if limit is not None:
            history = history[:limit]
        return history

    def get_alert_statistics(self) -> dict[str, object]:
        total_rules = len(self.rules)
        enabled_rules = sum(1 for r in self.rules.values() if r.enabled)
        active_alerts_by_severity: dict[str, int] = {}
        for alert in self.active_alerts.values():
            active_alerts_by_severity.setdefault(alert.severity.value, 0)
            active_alerts_by_severity[alert.severity.value] += 1

        alert_history_by_status: dict[str, int] = {}
        for alert in self.alert_history:
            alert_history_by_status.setdefault(alert.status.value, 0)
            alert_history_by_status[alert.status.value] += 1

        return {
            "active_alerts_count": len(self.active_alerts),
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "active_alerts_by_severity": active_alerts_by_severity,
            "alert_history_by_status": alert_history_by_status,
        }

    def add_notification_channel(self, name: str, channel: object) -> None:
        self.notification_channels[name] = channel


class AlertingService:
    def __init__(self) -> None:
        self.alert_manager = AlertManager()
        self.is_running = False

    def get_alert_manager(self) -> AlertManager:
        return self.alert_manager

    def add_notification_channel(self, name: str, channel_type: str, config: dict[str, object]) -> None:
        if channel_type == "email":
            channel = EmailNotificationChannel(name, config)
        elif channel_type == "webhook":
            channel = WebhookNotificationChannel(name, config)
        elif channel_type == "slack":
            channel = SlackNotificationChannel(name, config)
        else:
            raise ValueError(f"Unsupported channel type '{channel_type}'")
        self.alert_manager.add_notification_channel(name, channel)

    async def evaluate_metrics(self, metrics: dict[str, float]) -> None:
        await self.alert_manager.evaluate_all_alerts(metrics)

    def get_active_alerts(self) -> list[Alert]:
        return self.alert_manager.get_active_alerts()

    def get_alert_history(self, *, limit: int | None = None) -> list[Alert]:
        return self.alert_manager.get_alert_history(limit=limit)

    def get_alert_statistics(self) -> dict[str, object]:
        return self.alert_manager.get_alert_statistics()

    async def start(self) -> None:
        self.is_running = True

    async def stop(self) -> None:
        self.is_running = False


# Module-level singleton used by other components/tests
alerting_service = AlertingService()

