"""Monitoring dashboard API endpoints."""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from .logging_service import logging_service
from .metrics_service import metrics_service
from .alerting_service import alerting_service
from shared.auth import AuthManager


# Request/Response models
class LogQuery(BaseModel):
    """Log query parameters."""
    limit: int = Field(default=100, ge=1, le=1000)
    level: Optional[str] = None
    service: Optional[str] = None
    component: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class MetricsQuery(BaseModel):
    """Metrics query parameters."""
    metric_names: Optional[List[str]] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    interval: Optional[str] = None  # e.g., "1m", "5m", "1h"


class AlertQuery(BaseModel):
    """Alert query parameters."""
    limit: int = Field(default=100, ge=1, le=1000)
    status: Optional[str] = None
    severity: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class DashboardConfig(BaseModel):
    """Dashboard configuration."""
    refresh_interval: int = Field(default=30, ge=5, le=300)
    time_range: str = Field(default="1h")
    metrics: List[str] = Field(default_factory=list)
    alerts_enabled: bool = True
    logs_enabled: bool = True


class MonitoringEndpoints:
    """Monitoring dashboard API endpoints."""
    
    def __init__(self, auth_manager: AuthManager):
        """Initialize monitoring endpoints."""
        self.auth_manager = auth_manager
        self.router = APIRouter()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        # Log endpoints
        @self.router.get("/logs", response_model=Dict[str, Any])
        async def get_logs(
            limit: int = Query(default=100, ge=1, le=1000),
            level: Optional[str] = Query(default=None),
            service: Optional[str] = Query(default=None),
            component: Optional[str] = Query(default=None),
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get recent log entries."""
            try:
                logs = logging_service.get_recent_logs(
                    limit=limit,
                    level=level,
                    service=service,
                    component=component
                )
                
                return {
                    "success": True,
                    "data": {
                        "logs": logs,
                        "count": len(logs),
                        "filters": {
                            "level": level,
                            "service": service,
                            "component": component
                        }
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}") from e
        
        @self.router.get("/metrics/realtime", response_model=Dict[str, Any])
        async def get_realtime_metrics():
            """
            Get real-time metrics for animated dependencies visualization.
            Returns events/sec, active API calls, and active data sources.
            """
            try:
                # Calculate events per second from recent metrics
                events_metric = metrics_service.get_collector().get_metric("events_processed_total")
                events_per_second = 0.0
                
                if events_metric and len(events_metric.values) >= 2:
                    # Get events from last 5 seconds
                    recent_values = events_metric.values[-10:]  # Approximate
                    if len(recent_values) >= 2:
                        events_per_second = len(recent_values) / 5.0
                
                # Detect active data sources (simplified for Phase 1)
                active_sources = []
                
                # Check if we have recent metrics from each source
                if events_per_second > 0:
                    active_sources.append('home-assistant')
                
                # TODO: Add actual detection logic for sports APIs
                # For now, return mock data
                active_sources_count = len(active_sources)
                
                return {
                    "success": True,
                    "events_per_second": round(events_per_second, 2),
                    "active_api_calls": active_sources_count,
                    "active_sources": active_sources,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                # Graceful fallback
                return {
                    "success": False,
                    "events_per_second": 0,
                    "active_api_calls": 0,
                    "active_sources": [],
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
        
        @self.router.get("/logs/statistics", response_model=Dict[str, Any])
        async def get_log_statistics(
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get log statistics."""
            try:
                stats = logging_service.get_log_statistics()
                
                return {
                    "success": True,
                    "data": stats,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve log statistics: {str(e)}") from e
        
        @self.router.post("/logs/compress", response_model=Dict[str, Any])
        async def compress_logs(
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Compress old log files."""
            try:
                compressed_count = logging_service.compress_old_logs()
                
                return {
                    "success": True,
                    "data": {
                        "compressed_files": compressed_count
                    },
                    "message": f"Compressed {compressed_count} log files",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to compress logs: {str(e)}") from e
        
        @self.router.delete("/logs/cleanup", response_model=Dict[str, Any])
        async def cleanup_old_logs(
            days_to_keep: int = Query(default=30, ge=1, le=365),
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Cleanup old compressed log files."""
            try:
                deleted_count = logging_service.cleanup_old_compressed_logs(days_to_keep)
                
                return {
                    "success": True,
                    "data": {
                        "deleted_files": deleted_count,
                        "days_to_keep": days_to_keep
                    },
                    "message": f"Deleted {deleted_count} old log files",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to cleanup logs: {str(e)}") from e
        
        # Metrics endpoints
        @self.router.get("/metrics", response_model=Dict[str, Any])
        async def get_metrics(
            metric_names: Optional[List[str]] = Query(default=None),
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get metrics."""
            try:
                metrics = metrics_service.get_metrics(metric_names)
                metrics_data = [metric.to_dict() for metric in metrics]
                
                return {
                    "success": True,
                    "data": {
                        "metrics": metrics_data,
                        "count": len(metrics_data)
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}") from e
        
        @self.router.get("/metrics/current", response_model=Dict[str, Any])
        async def get_current_metrics(
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get current metric values."""
            try:
                current_metrics = metrics_service.get_current_metrics()
                
                return {
                    "success": True,
                    "data": current_metrics,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve current metrics: {str(e)}") from e
        
        @self.router.get("/metrics/summary", response_model=Dict[str, Any])
        async def get_metrics_summary(
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get metrics summary."""
            try:
                summary = metrics_service.get_metrics_summary()
                
                return {
                    "success": True,
                    "data": summary,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics summary: {str(e)}") from e
        
        # Alert endpoints
        @self.router.get("/alerts", response_model=Dict[str, Any])
        async def get_alerts(
            limit: int = Query(default=100, ge=1, le=1000),
            status: Optional[str] = Query(default=None),
            severity: Optional[str] = Query(default=None),
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get alerts."""
            try:
                alert_manager = alerting_service.get_alert_manager()
                
                # Convert string parameters to enums if provided
                from shared.monitoring.alerting_service import AlertStatus, AlertSeverity
                status_enum = None
                severity_enum = None
                
                if status:
                    try:
                        status_enum = AlertStatus(status)
                    except ValueError as err:
                        raise HTTPException(status_code=400, detail=f"Invalid status: {status}") from err
                
                if severity:
                    try:
                        severity_enum = AlertSeverity(severity)
                    except ValueError as err:
                        raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}") from err
                
                alerts = alert_manager.get_alert_history(
                    limit=limit,
                    status=status_enum,
                    severity=severity_enum
                )
                
                alerts_data = [alert.to_dict() for alert in alerts]
                
                return {
                    "success": True,
                    "data": {
                        "alerts": alerts_data,
                        "count": len(alerts_data),
                        "filters": {
                            "status": status,
                            "severity": severity
                        }
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}") from e
        
        @self.router.get("/alerts/active", response_model=Dict[str, Any])
        async def get_active_alerts(
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get active alerts."""
            try:
                active_alerts = alerting_service.get_active_alerts()
                alerts_data = [alert.to_dict() for alert in active_alerts]
                
                return {
                    "success": True,
                    "data": {
                        "alerts": alerts_data,
                        "count": len(alerts_data)
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve active alerts: {str(e)}") from e
        
        @self.router.get("/alerts/statistics", response_model=Dict[str, Any])
        async def get_alert_statistics(
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get alert statistics."""
            try:
                alert_manager = alerting_service.get_alert_manager()
                stats = alert_manager.get_alert_statistics()
                
                return {
                    "success": True,
                    "data": stats,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve alert statistics: {str(e)}") from e
        
        @self.router.post("/alerts/{alert_id}/acknowledge", response_model=Dict[str, Any])
        async def acknowledge_alert(
            alert_id: str,
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Acknowledge an alert."""
            try:
                alert_manager = alerting_service.get_alert_manager()
                user_id = current_user.get('user_id', 'unknown')
                
                success = alert_manager.acknowledge_alert(alert_id, user_id)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Alert not found")
                
                return {
                    "success": True,
                    "message": "Alert acknowledged successfully",
                    "timestamp": datetime.now().isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}") from e
        
        @self.router.post("/alerts/{alert_id}/resolve", response_model=Dict[str, Any])
        async def resolve_alert(
            alert_id: str,
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Resolve an alert."""
            try:
                alert_manager = alerting_service.get_alert_manager()
                user_id = current_user.get('user_id', 'unknown')
                
                success = alert_manager.resolve_alert(alert_id, user_id)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Alert not found")
                
                return {
                    "success": True,
                    "message": "Alert resolved successfully",
                    "timestamp": datetime.now().isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}") from e
        
        # Dashboard endpoints
        @self.router.get("/dashboard/overview", response_model=Dict[str, Any])
        async def get_dashboard_overview(
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get dashboard overview data."""
            try:
                # Get current metrics
                current_metrics = metrics_service.get_current_metrics()
                
                # Get active alerts
                active_alerts = alerting_service.get_active_alerts()
                alerts_data = [alert.to_dict() for alert in active_alerts]
                
                # Get recent logs
                recent_logs = logging_service.get_recent_logs(limit=50)
                
                # Get log statistics
                log_stats = logging_service.get_log_statistics()
                
                # Get alert statistics
                alert_manager = alerting_service.get_alert_manager()
                alert_stats = alert_manager.get_alert_statistics()
                
                return {
                    "success": True,
                    "data": {
                        "current_metrics": current_metrics,
                        "active_alerts": alerts_data,
                        "recent_logs": recent_logs,
                        "log_statistics": log_stats,
                        "alert_statistics": alert_stats,
                        "system_status": {
                            "logging_service": logging_service.is_running,
                            "metrics_service": metrics_service.is_running,
                            "alerting_service": alerting_service.is_running
                        }
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboard overview: {str(e)}") from e
        
        @self.router.get("/dashboard/health", response_model=Dict[str, Any])
        async def get_dashboard_health(
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get dashboard health status."""
            try:
                # Check service health
                services_healthy = {
                    "logging_service": logging_service.is_running,
                    "metrics_service": metrics_service.is_running,
                    "alerting_service": alerting_service.is_running
                }
                
                # Check for critical alerts
                active_alerts = alerting_service.get_active_alerts()
                critical_alerts = [alert for alert in active_alerts 
                                 if alert.severity.value == "critical"]
                
                # Overall health status
                overall_healthy = (
                    all(services_healthy.values()) and 
                    len(critical_alerts) == 0
                )
                
                return {
                    "success": True,
                    "data": {
                        "overall_healthy": overall_healthy,
                        "services": services_healthy,
                        "critical_alerts_count": len(critical_alerts),
                        "active_alerts_count": len(active_alerts),
                        "last_check": datetime.now().isoformat()
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboard health: {str(e)}") from e
        
        # Configuration endpoints
        @self.router.get("/config/alert-rules", response_model=Dict[str, Any])
        async def get_alert_rules(
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Get alert rules configuration."""
            try:
                alert_manager = alerting_service.get_alert_manager()
                rules = alert_manager.get_all_rules()
                rules_data = [rule.to_dict() for rule in rules]
                
                return {
                    "success": True,
                    "data": {
                        "rules": rules_data,
                        "count": len(rules_data)
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve alert rules: {str(e)}") from e
        
        @self.router.post("/config/alert-rules", response_model=Dict[str, Any])
        async def create_alert_rule(
            rule_data: Dict[str, Any],
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Create a new alert rule."""
            try:
                from shared.monitoring.alerting_service import AlertRule, AlertSeverity
                
                # Validate and create alert rule
                rule = AlertRule(
                    name=rule_data["name"],
                    description=rule_data["description"],
                    metric_name=rule_data["metric_name"],
                    condition=rule_data["condition"],
                    threshold=rule_data["threshold"],
                    severity=AlertSeverity(rule_data["severity"]),
                    enabled=rule_data.get("enabled", True),
                    cooldown_minutes=rule_data.get("cooldown_minutes", 5),
                    notification_channels=rule_data.get("notification_channels", [])
                )
                
                alert_manager = alerting_service.get_alert_manager()
                alert_manager.add_rule(rule)
                
                return {
                    "success": True,
                    "data": rule.to_dict(),
                    "message": "Alert rule created successfully",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to create alert rule: {str(e)}") from e
        
        @self.router.put("/config/alert-rules/{rule_name}", response_model=Dict[str, Any])
        async def update_alert_rule(
            rule_name: str,
            rule_data: Dict[str, Any],
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Update an alert rule."""
            try:
                from shared.monitoring.alerting_service import AlertRule, AlertSeverity
                
                # Validate and create alert rule
                rule = AlertRule(
                    name=rule_name,
                    description=rule_data["description"],
                    metric_name=rule_data["metric_name"],
                    condition=rule_data["condition"],
                    threshold=rule_data["threshold"],
                    severity=AlertSeverity(rule_data["severity"]),
                    enabled=rule_data.get("enabled", True),
                    cooldown_minutes=rule_data.get("cooldown_minutes", 5),
                    notification_channels=rule_data.get("notification_channels", [])
                )
                
                alert_manager = alerting_service.get_alert_manager()
                alert_manager.update_rule(rule)
                
                return {
                    "success": True,
                    "data": rule.to_dict(),
                    "message": "Alert rule updated successfully",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to update alert rule: {str(e)}") from e
        
        @self.router.delete("/config/alert-rules/{rule_name}", response_model=Dict[str, Any])
        async def delete_alert_rule(
            rule_name: str,
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Delete an alert rule."""
            try:
                alert_manager = alerting_service.get_alert_manager()
                alert_manager.remove_rule(rule_name)
                
                return {
                    "success": True,
                    "message": "Alert rule deleted successfully",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to delete alert rule: {str(e)}") from e
        
        @self.router.post("/config/notification-channels", response_model=Dict[str, Any])
        async def create_notification_channel(
            channel_data: Dict[str, Any],
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Create a notification channel."""
            try:
                channel_name = channel_data["name"]
                channel_type = channel_data["type"]
                config = channel_data["config"]
                
                alerting_service.add_notification_channel(channel_name, channel_type, config)
                
                return {
                    "success": True,
                    "message": "Notification channel created successfully",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to create notification channel: {str(e)}") from e
        
        # Export endpoints
        @self.router.get("/export/logs", response_model=Dict[str, Any])
        async def export_logs(
            format: str = Query(default="json", regex="^(json|csv)$"),
            limit: int = Query(default=1000, ge=1, le=10000),
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Export logs in specified format."""
            try:
                logs = logging_service.get_recent_logs(limit=limit)
                
                if format == "json":
                    return {
                        "success": True,
                        "data": {
                            "logs": logs,
                            "format": "json",
                            "count": len(logs)
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                elif format == "csv":
                    # Convert to CSV format
                    import csv
                    import io
                    
                    output = io.StringIO()
                    if logs:
                        fieldnames = logs[0].keys()
                        writer = csv.DictWriter(output, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(logs)
                    
                    return {
                        "success": True,
                        "data": {
                            "csv_data": output.getvalue(),
                            "format": "csv",
                            "count": len(logs)
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to export logs: {str(e)}") from e
        
        @self.router.get("/export/metrics", response_model=Dict[str, Any])
        async def export_metrics(
            format: str = Query(default="json", regex="^(json|csv)$"),
            metric_names: Optional[List[str]] = Query(default=None),
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Export metrics in specified format."""
            try:
                metrics = metrics_service.get_metrics(metric_names)
                metrics_data = [metric.to_dict() for metric in metrics]
                
                if format == "json":
                    return {
                        "success": True,
                        "data": {
                            "metrics": metrics_data,
                            "format": "json",
                            "count": len(metrics_data)
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                elif format == "csv":
                    # Convert to CSV format
                    import csv
                    import io
                    
                    output = io.StringIO()
                    if metrics_data:
                        # Flatten metrics data for CSV
                        csv_data = []
                        for metric in metrics_data:
                            for value in metric.get("values", []):
                                csv_data.append({
                                    "metric_name": metric["name"],
                                    "metric_type": metric["type"],
                                    "timestamp": value["timestamp"],
                                    "value": value["value"],
                                    "unit": metric["unit"]
                                })
                        
                        if csv_data:
                            fieldnames = csv_data[0].keys()
                            writer = csv.DictWriter(output, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(csv_data)
                    
                    return {
                        "success": True,
                        "data": {
                            "csv_data": output.getvalue(),
                            "format": "csv",
                            "count": len(csv_data) if csv_data else 0
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to export metrics: {str(e)}") from e
        
        @self.router.get("/export/alerts", response_model=Dict[str, Any])
        async def export_alerts(
            format: str = Query(default="json", regex="^(json|csv)$"),
            limit: int = Query(default=1000, ge=1, le=10000),
            current_user: Dict[str, Any] = Depends(self.auth_manager.get_current_user)
        ):
            """Export alerts in specified format."""
            try:
                alert_manager = alerting_service.get_alert_manager()
                alerts = alert_manager.get_alert_history(limit=limit)
                alerts_data = [alert.to_dict() for alert in alerts]
                
                if format == "json":
                    return {
                        "success": True,
                        "data": {
                            "alerts": alerts_data,
                            "format": "json",
                            "count": len(alerts_data)
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                elif format == "csv":
                    # Convert to CSV format
                    import csv
                    import io
                    
                    output = io.StringIO()
                    if alerts_data:
                        fieldnames = alerts_data[0].keys()
                        writer = csv.DictWriter(output, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(alerts_data)
                    
                    return {
                        "success": True,
                        "data": {
                            "csv_data": output.getvalue(),
                            "format": "csv",
                            "count": len(alerts_data)
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to export alerts: {str(e)}") from e
