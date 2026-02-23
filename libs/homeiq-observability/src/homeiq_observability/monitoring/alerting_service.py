"""Configurable alerting system for monitoring and notifications."""

import asyncio
import json
import smtplib
import requests
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
from collections import defaultdict


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    description: str
    metric_name: str
    condition: str  # e.g., ">", "<", "==", "!="
    threshold: float
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 5
    notification_channels: List[str] = None
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert rule to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "metric_name": self.metric_name,
            "condition": self.condition,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "cooldown_minutes": self.cooldown_minutes,
            "notification_channels": self.notification_channels
        }


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    condition: str
    status: AlertStatus
    created_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return asdict(self)


class NotificationChannel:
    """Base class for notification channels."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize notification channel."""
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
    
    async def send_notification(self, alert: Alert) -> bool:
        """Send notification for an alert."""
        raise NotImplementedError


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize email notification channel."""
        super().__init__(name, config)
        self.smtp_server = config.get('smtp_server', 'localhost')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config.get('from_email')
        self.to_emails = config.get('to_emails', [])
        self.use_tls = config.get('use_tls', True)
    
    async def send_notification(self, alert: Alert) -> bool:
        """Send email notification."""
        if not self.enabled or not self.to_emails:
            return False
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.rule_name}"
            
            # Create email body
            body = f"""
Alert Details:
- Rule: {alert.rule_name}
- Severity: {alert.severity.value.upper()}
- Message: {alert.message}
- Metric: {alert.metric_name} = {alert.metric_value}
- Condition: {alert.condition} {alert.threshold}
- Created: {alert.created_at}
- Alert ID: {alert.alert_id}

This is an automated alert from the Home Assistant Ingestor monitoring system.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to send email notification: {e}")
            return False


class WebhookNotificationChannel(NotificationChannel):
    """Webhook notification channel."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize webhook notification channel."""
        super().__init__(name, config)
        self.webhook_url = config.get('webhook_url')
        self.headers = config.get('headers', {'Content-Type': 'application/json'})
        self.timeout = config.get('timeout', 10)
    
    async def send_notification(self, alert: Alert) -> bool:
        """Send webhook notification."""
        if not self.enabled or not self.webhook_url:
            return False
        
        try:
            payload = {
                "alert": alert.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "homeiq-monitoring"
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logging.error(f"Failed to send webhook notification: {e}")
            return False


class SlackNotificationChannel(NotificationChannel):
    """Slack notification channel."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize Slack notification channel."""
        super().__init__(name, config)
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel', '#alerts')
        self.username = config.get('username', 'HomeIQ')
        self.icon_emoji = config.get('icon_emoji', ':warning:')
    
    async def send_notification(self, alert: Alert) -> bool:
        """Send Slack notification."""
        if not self.enabled or not self.webhook_url:
            return False
        
        try:
            # Determine color based on severity
            color_map = {
                AlertSeverity.INFO: "good",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.CRITICAL: "danger"
            }
            
            payload = {
                "channel": self.channel,
                "username": self.username,
                "icon_emoji": self.icon_emoji,
                "attachments": [{
                    "color": color_map.get(alert.severity, "warning"),
                    "title": f"[{alert.severity.value.upper()}] {alert.rule_name}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Metric",
                            "value": f"{alert.metric_name} = {alert.metric_value}",
                            "short": True
                        },
                        {
                            "title": "Condition",
                            "value": f"{alert.condition} {alert.threshold}",
                            "short": True
                        },
                        {
                            "title": "Alert ID",
                            "value": alert.alert_id,
                            "short": True
                        }
                    ],
                    "ts": int(datetime.fromisoformat(alert.created_at.replace('Z', '+00:00')).timestamp())
                }]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logging.error(f"Failed to send Slack notification: {e}")
            return False


class AlertManager:
    """Alert management and evaluation."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.cooldown_timers: Dict[str, datetime] = {}
        self.alert_lock = threading.Lock()
        
        # Configuration
        self.max_history_size = int(os.getenv('ALERT_MAX_HISTORY_SIZE', '10000'))
        self.alert_evaluation_interval = float(os.getenv('ALERT_EVALUATION_INTERVAL_SECONDS', '30'))
        
        # Background processing
        self.is_evaluating = False
        self.evaluation_task = None
        
        # Load default configuration
        self._load_default_configuration()
    
    def _load_default_configuration(self):
        """Load default alert configuration."""
        # High CPU usage alert
        self.add_rule(AlertRule(
            name="high_cpu_usage",
            description="CPU usage is above 80%",
            metric_name="system_cpu_usage_percent",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.WARNING,
            cooldown_minutes=5
        ))
        
        # Critical CPU usage alert
        self.add_rule(AlertRule(
            name="critical_cpu_usage",
            description="CPU usage is above 95%",
            metric_name="system_cpu_usage_percent",
            condition=">",
            threshold=95.0,
            severity=AlertSeverity.CRITICAL,
            cooldown_minutes=2
        ))
        
        # High memory usage alert
        self.add_rule(AlertRule(
            name="high_memory_usage",
            description="Memory usage is above 85%",
            metric_name="system_memory_usage_percent",
            condition=">",
            threshold=85.0,
            severity=AlertSeverity.WARNING,
            cooldown_minutes=5
        ))
        
        # Critical memory usage alert
        self.add_rule(AlertRule(
            name="critical_memory_usage",
            description="Memory usage is above 95%",
            metric_name="system_memory_usage_percent",
            condition=">",
            threshold=95.0,
            severity=AlertSeverity.CRITICAL,
            cooldown_minutes=2
        ))
        
        # High disk usage alert
        self.add_rule(AlertRule(
            name="high_disk_usage",
            description="Disk usage is above 90%",
            metric_name="system_disk_usage_percent",
            condition=">",
            threshold=90.0,
            severity=AlertSeverity.WARNING,
            cooldown_minutes=10
        ))
        
        # High error rate alert
        self.add_rule(AlertRule(
            name="high_error_rate",
            description="Error rate is above 10 errors per minute",
            metric_name="errors_total",
            condition=">",
            threshold=10.0,
            severity=AlertSeverity.WARNING,
            cooldown_minutes=5
        ))
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.name] = rule
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
    
    def update_rule(self, rule: AlertRule):
        """Update an alert rule."""
        self.rules[rule.name] = rule
    
    def get_rule(self, rule_name: str) -> Optional[AlertRule]:
        """Get an alert rule."""
        return self.rules.get(rule_name)
    
    def get_all_rules(self) -> List[AlertRule]:
        """Get all alert rules."""
        return list(self.rules.values())
    
    def add_notification_channel(self, name: str, channel: NotificationChannel):
        """Add a notification channel."""
        self.notification_channels[name] = channel
    
    def remove_notification_channel(self, name: str):
        """Remove a notification channel."""
        if name in self.notification_channels:
            del self.notification_channels[name]
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate alert condition."""
        if condition == ">":
            return value > threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<":
            return value < threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return value == threshold
        elif condition == "!=":
            return value != threshold
        else:
            return False
    
    def _is_in_cooldown(self, rule_name: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule_name not in self.cooldown_timers:
            return False
        
        cooldown_time = self.cooldown_timers[rule_name]
        rule = self.rules.get(rule_name)
        if not rule:
            return False
        
        cooldown_duration = timedelta(minutes=rule.cooldown_minutes)
        return datetime.now(timezone.utc) - cooldown_time < cooldown_duration
    
    def _set_cooldown(self, rule_name: str):
        """Set cooldown timer for rule."""
        self.cooldown_timers[rule_name] = datetime.now(timezone.utc)
    
    async def evaluate_alert(self, rule_name: str, metric_value: float) -> Optional[Alert]:
        """Evaluate a single alert rule."""
        rule = self.rules.get(rule_name)
        if not rule or not rule.enabled:
            return None
        
        # Check cooldown
        if self._is_in_cooldown(rule_name):
            return None
        
        # Evaluate condition
        if not self._evaluate_condition(metric_value, rule.condition, rule.threshold):
            # Condition not met, resolve any active alert
            if rule_name in self.active_alerts:
                alert = self.active_alerts[rule_name]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc).isoformat()
                del self.active_alerts[rule_name]
            return None
        
        # Condition met, check if alert already exists
        if rule_name in self.active_alerts:
            return self.active_alerts[rule_name]
        
        # Create new alert
        alert_id = f"{rule_name}_{int(datetime.now().timestamp())}"
        alert = Alert(
            alert_id=alert_id,
            rule_name=rule_name,
            severity=rule.severity,
            message=rule.description,
            metric_name=rule.metric_name,
            metric_value=metric_value,
            threshold=rule.threshold,
            condition=rule.condition,
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        with self.alert_lock:
            self.active_alerts[rule_name] = alert
            self.alert_history.append(alert)
            
            # Limit history size
            if len(self.alert_history) > self.max_history_size:
                self.alert_history = self.alert_history[-self.max_history_size:]
        
        # Set cooldown
        self._set_cooldown(rule_name)
        
        # Send notifications
        await self._send_notifications(alert, rule)
        
        return alert
    
    async def _send_notifications(self, alert: Alert, rule: AlertRule):
        """Send notifications for an alert."""
        notification_tasks = []
        
        for channel_name in rule.notification_channels:
            if channel_name in self.notification_channels:
                channel = self.notification_channels[channel_name]
                task = asyncio.create_task(channel.send_notification(alert))
                notification_tasks.append(task)
        
        if notification_tasks:
            await asyncio.gather(*notification_tasks, return_exceptions=True)
    
    async def evaluate_all_alerts(self, metrics: Dict[str, float]):
        """Evaluate all alert rules against current metrics."""
        evaluation_tasks = []
        
        for rule_name, rule in self.rules.items():
            if rule.metric_name in metrics:
                metric_value = metrics[rule.metric_name]
                task = asyncio.create_task(self.evaluate_alert(rule_name, metric_value))
                evaluation_tasks.append(task)
        
        if evaluation_tasks:
            await asyncio.gather(*evaluation_tasks, return_exceptions=True)
    
    async def start_evaluation(self):
        """Start background alert evaluation."""
        if self.is_evaluating:
            return
        
        self.is_evaluating = True
        self.evaluation_task = asyncio.create_task(self._evaluation_loop())
    
    async def stop_evaluation(self):
        """Stop background alert evaluation."""
        if not self.is_evaluating:
            return
        
        self.is_evaluating = False
        if self.evaluation_task:
            self.evaluation_task.cancel()
            try:
                await self.evaluation_task
            except asyncio.CancelledError:
                pass
    
    async def _evaluation_loop(self):
        """Background alert evaluation loop."""
        while self.is_evaluating:
            try:
                # This would typically get current metrics from the metrics service
                # For now, we'll skip the actual evaluation in the loop
                # The evaluation will be triggered by external calls
                await asyncio.sleep(self.alert_evaluation_interval)
                
            except Exception as e:
                logging.error(f"Error in alert evaluation loop: {e}")
                await asyncio.sleep(5)
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        with self.alert_lock:
            for alert in self.active_alerts.values():
                if alert.alert_id == alert_id:
                    alert.status = AlertStatus.ACKNOWLEDGED
                    alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
                    alert.acknowledged_by = acknowledged_by
                    return True
            
            # Check in history
            for alert in self.alert_history:
                if alert.alert_id == alert_id:
                    alert.status = AlertStatus.ACKNOWLEDGED
                    alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
                    alert.acknowledged_by = acknowledged_by
                    return True
        
        return False
    
    def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve an alert."""
        with self.alert_lock:
            # Remove from active alerts
            for rule_name, alert in list(self.active_alerts.items()):
                if alert.alert_id == alert_id:
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now(timezone.utc).isoformat()
                    alert.resolved_by = resolved_by
                    del self.active_alerts[rule_name]
                    return True
            
            # Update in history
            for alert in self.alert_history:
                if alert.alert_id == alert_id:
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now(timezone.utc).isoformat()
                    alert.resolved_by = resolved_by
                    return True
        
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        with self.alert_lock:
            return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100, 
                         status: Optional[AlertStatus] = None,
                         severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get alert history."""
        with self.alert_lock:
            alerts = self.alert_history.copy()
        
        # Apply filters
        if status:
            alerts = [alert for alert in alerts if alert.status == status]
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        # Sort by creation time (newest first) and limit
        alerts.sort(key=lambda x: x.created_at, reverse=True)
        return alerts[:limit]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        with self.alert_lock:
            active_alerts = list(self.active_alerts.values())
            history = self.alert_history.copy()
        
        # Count by severity
        severity_counts = defaultdict(int)
        for alert in active_alerts:
            severity_counts[alert.severity.value] += 1
        
        # Count by status in history
        status_counts = defaultdict(int)
        for alert in history:
            status_counts[alert.status.value] += 1
        
        return {
            "active_alerts_count": len(active_alerts),
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
            "active_alerts_by_severity": dict(severity_counts),
            "alert_history_by_status": dict(status_counts),
            "total_notification_channels": len(self.notification_channels),
            "enabled_notification_channels": len([c for c in self.notification_channels.values() if c.enabled])
        }


class AlertingService:
    """Main alerting service for the application."""
    
    def __init__(self):
        """Initialize alerting service."""
        self.alert_manager = AlertManager()
        self.is_running = False
    
    async def start(self):
        """Start the alerting service."""
        if self.is_running:
            return
        
        await self.alert_manager.start_evaluation()
        self.is_running = True
    
    async def stop(self):
        """Stop the alerting service."""
        if not self.is_running:
            return
        
        await self.alert_manager.stop_evaluation()
        self.is_running = False
    
    def get_alert_manager(self) -> AlertManager:
        """Get alert manager."""
        return self.alert_manager
    
    def add_notification_channel(self, name: str, channel_type: str, config: Dict[str, Any]):
        """Add a notification channel."""
        if channel_type == "email":
            channel = EmailNotificationChannel(name, config)
        elif channel_type == "webhook":
            channel = WebhookNotificationChannel(name, config)
        elif channel_type == "slack":
            channel = SlackNotificationChannel(name, config)
        else:
            raise ValueError(f"Unknown notification channel type: {channel_type}")
        
        self.alert_manager.add_notification_channel(name, channel)
    
    async def evaluate_metrics(self, metrics: Dict[str, float]):
        """Evaluate metrics against alert rules."""
        await self.alert_manager.evaluate_all_alerts(metrics)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get active alerts."""
        return self.alert_manager.get_active_alerts()
    
    def get_alert_history(self, **kwargs) -> List[Alert]:
        """Get alert history."""
        return self.alert_manager.get_alert_history(**kwargs)
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        return self.alert_manager.get_alert_statistics()


# Global alerting service instance
alerting_service = AlertingService()
