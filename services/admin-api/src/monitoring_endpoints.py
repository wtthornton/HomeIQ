"""
Monitoring endpoints for the admin API.

Provides lightweight implementations required by the unit tests. The endpoints
delegate to in-memory services defined in sibling modules so they can operate
without external infrastructure.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from .alerting_service import AlertingService, AlertRule, AlertSeverity
from .auth import AuthManager
from .logging_service import LoggingService
from .metrics_service import MetricsService

logging_service = LoggingService()
metrics_service = MetricsService()
alerting_service = AlertingService()


def _success(data: dict[str, Any], message: str = "OK") -> dict[str, Any]:
    return {"success": True, "message": message, "data": data}


class MonitoringEndpoints:
    def __init__(self, auth_manager: AuthManager) -> None:
        self.auth_manager = auth_manager
        self.router = APIRouter(tags=["Monitoring"])
        self._register_routes()

    def _register_routes(self) -> None:
        router = self.router

        @router.get("/logs")
        async def get_logs(
            limit: int = Query(default=100, ge=1, le=1000),
            level: str | None = None,
            service: str | None = None,
            component: str | None = None,
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            logs = logging_service.get_recent_logs(
                limit=limit,
                level=level,
                service=service,
                component=component,
            )
            return _success({"logs": logs}, "Logs retrieved successfully")

        @router.get("/logs/statistics")
        async def get_log_statistics(
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            stats = logging_service.get_log_statistics()
            return _success(stats, "Log statistics retrieved successfully")

        @router.post("/logs/compress")
        async def compress_logs(
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            compressed = logging_service.compress_old_logs()
            return _success(
                {"compressed_files": compressed},
                f"Compressed {compressed} log files",
            )

        @router.delete("/logs/cleanup")
        async def cleanup_old_logs(
            days_to_keep: int = Query(default=30, ge=1, le=365),
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            deleted = logging_service.cleanup_old_compressed_logs(days_to_keep)
            return _success(
                {"deleted_files": deleted, "days_to_keep": days_to_keep},
                f"Deleted {deleted} old compressed log files",
            )

        @router.get("/metrics")
        async def get_metrics(
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            metrics = metrics_service.get_metrics()
            return _success({"metrics": metrics}, "Metrics retrieved successfully")

        @router.get("/metrics/current")
        async def get_current_metrics(
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            current_metrics = metrics_service.get_current_metrics()
            return _success(current_metrics, "Current metrics retrieved successfully")

        @router.get("/metrics/summary")
        async def get_metrics_summary(
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            summary = metrics_service.get_metrics_summary()
            return _success(summary, "Metrics summary retrieved successfully")

        @router.get("/alerts")
        async def get_alerts(
            limit: int = Query(default=50, ge=1, le=500),
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            alerts = alerting_service.get_alert_manager().get_alert_history(limit=limit)
            return _success({"alerts": [alert.to_dict() for alert in alerts]}, "Alerts retrieved successfully")

        @router.get("/alerts/active")
        async def get_active_alerts(
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            alerts = alerting_service.get_active_alerts()
            return _success({"alerts": [alert.to_dict() for alert in alerts]}, "Active alerts retrieved successfully")

        @router.get("/alerts/statistics")
        async def get_alert_statistics(
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            stats = alerting_service.get_alert_manager().get_alert_statistics()
            return _success(stats, "Alert statistics retrieved successfully")

        @router.post("/alerts/{alert_id}/acknowledge")
        async def acknowledge_alert(
            alert_id: str,
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            success = alerting_service.get_alert_manager().acknowledge_alert(alert_id, current_user.get("user_id"))
            if not success:
                raise HTTPException(status_code=404, detail="Alert not found")
            return _success({}, f"Alert {alert_id} acknowledged successfully")

        @router.post("/alerts/{alert_id}/resolve")
        async def resolve_alert(
            alert_id: str,
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            success = alerting_service.get_alert_manager().resolve_alert(alert_id, current_user.get("user_id"))
            if not success:
                raise HTTPException(status_code=404, detail="Alert not found")
            return _success({}, f"Alert {alert_id} resolved successfully")

        @router.get("/dashboard/overview")
        async def get_dashboard_overview(
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            overview = {
                "current_metrics": metrics_service.get_current_metrics(),
                "metrics_summary": metrics_service.get_metrics_summary(),
                "active_alerts": [alert.to_dict() for alert in alerting_service.get_active_alerts()],
                "alert_statistics": alerting_service.get_alert_manager().get_alert_statistics(),
                "recent_logs": logging_service.get_recent_logs(limit=20),
                "log_statistics": logging_service.get_log_statistics(),
                "system_status": {
                    "logging_service_running": logging_service.is_running,
                    "metrics_service_running": metrics_service.is_running,
                    "alerting_service_running": alerting_service.is_running,
                },
            }
            return _success(overview, "Dashboard overview retrieved successfully")

        @router.get("/dashboard/health")
        async def get_dashboard_health(
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            active_alerts = alerting_service.get_active_alerts()
            critical_alerts = [alert for alert in active_alerts if alert.severity == AlertSeverity.CRITICAL]
            health = {
                "overall_healthy": len(critical_alerts) == 0,
                "active_alerts_count": len(active_alerts),
                "critical_alerts_count": len(critical_alerts),
                "services": {
                    "logging": logging_service.is_running,
                    "metrics": metrics_service.is_running,
                    "alerting": alerting_service.is_running,
                },
            }
            return _success(health, "Dashboard health retrieved successfully")

        @router.get("/config/alert-rules")
        async def get_alert_rules(
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            rules = alerting_service.get_alert_manager().get_all_rules()
            if rules is None:
                rules = []
            return _success({"rules": [rule.to_dict() for rule in rules]}, "Alert rules retrieved successfully")

        @router.post("/config/alert-rules")
        async def create_alert_rule(
            payload: dict[str, Any],
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            rule = AlertRule(
                name=payload["name"],
                description=payload.get("description", ""),
                metric_name=payload["metric_name"],
                condition=payload["condition"],
                threshold=float(payload["threshold"]),
                severity=AlertSeverity(payload.get("severity", "warning")),
                enabled=payload.get("enabled", True),
                cooldown_minutes=payload.get("cooldown_minutes", 5),
                notification_channels=payload.get("notification_channels", []),
            )
            alerting_service.get_alert_manager().add_rule(rule)
            return _success({}, f"Alert rule '{rule.name}' created successfully")

        @router.put("/config/alert-rules/{rule_name}")
        async def update_alert_rule(
            rule_name: str,
            payload: dict[str, Any],
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            updated_rule = AlertRule(
                name=rule_name,
                description=payload.get("description", ""),
                metric_name=payload["metric_name"],
                condition=payload["condition"],
                threshold=float(payload["threshold"]),
                severity=AlertSeverity(payload.get("severity", "warning")),
                enabled=payload.get("enabled", True),
                cooldown_minutes=payload.get("cooldown_minutes", 5),
                notification_channels=payload.get("notification_channels", []),
            )
            alerting_service.get_alert_manager().update_rule(updated_rule)
            return _success({}, f"Alert rule '{rule_name}' updated successfully")

        @router.delete("/config/alert-rules/{rule_name}")
        async def delete_alert_rule(
            rule_name: str,
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            alerting_service.get_alert_manager().remove_rule(rule_name)
            return _success({}, f"Alert rule '{rule_name}' deleted successfully")

        @router.post("/config/notification-channels")
        async def create_notification_channel(
            payload: dict[str, Any],
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            alerting_service.add_notification_channel(payload["name"], payload["type"], payload.get("config", {}))
            return _success({}, f"Notification channel '{payload['name']}' created successfully")

        @router.get("/export/logs")
        async def export_logs(
            format: str = Query(default="json", pattern="^(json|csv)$"),
            limit: int = Query(default=100, ge=1, le=1000),
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            logs = logging_service.get_recent_logs(limit=limit)
            if format == "csv":
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=["timestamp", "level", "service", "component", "message"])
                writer.writeheader()
                for log in logs:
                    writer.writerow(log)
                return _success({"format": "csv", "csv_data": output.getvalue()}, "Logs exported as CSV")
            return _success({"format": "json", "logs": logs}, "Logs exported as JSON")

        @router.get("/export/metrics")
        async def export_metrics(
            format: str = Query(default="json", pattern="^(json)$"),
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            metrics = metrics_service.get_metrics()
            return _success({"format": format, "metrics": metrics}, "Metrics exported")

        @router.get("/export/alerts")
        async def export_alerts(
            format: str = Query(default="json", pattern="^(json)$"),
            limit: int = Query(default=100, ge=1, le=1000),
            current_user: dict[str, Any] = Depends(self.auth_manager.get_current_user),
        ):
            alerts = alerting_service.get_alert_manager().get_alert_history(limit=limit)
            return _success({"format": format, "alerts": [alert.to_dict() for alert in alerts]}, "Alerts exported")

