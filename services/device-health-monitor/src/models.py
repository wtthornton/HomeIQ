"""
Health Report Models
Phase 1.2: Data models for device health reports
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HealthSeverity(str, Enum):
    """Health issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthIssue(BaseModel):
    """Individual health issue"""
    type: str = Field(description="Issue type (e.g., 'slow_response', 'low_battery')")
    severity: HealthSeverity = Field(description="Severity level")
    message: str = Field(description="Human-readable message")
    details: dict[str, Any] | None = Field(default=None, description="Additional details")


class MaintenanceRecommendation(BaseModel):
    """Maintenance recommendation"""
    title: str = Field(description="Recommendation title")
    description: str = Field(description="Detailed description")
    priority: str = Field(description="Priority: low, medium, high")
    action: str | None = Field(default=None, description="Recommended action")


class DeviceHealthReport(BaseModel):
    """Complete device health report"""
    device_id: str = Field(description="Device identifier")
    device_name: str = Field(description="Device name")
    timestamp: str = Field(description="Report timestamp")
    overall_status: str = Field(description="Overall status: healthy, warning, error")
    response_time_ms: float | None = Field(default=None, description="Average response time in milliseconds")
    battery_level: float | None = Field(default=None, description="Battery level (0-100)")
    last_seen: str | None = Field(default=None, description="Last seen timestamp")
    power_consumption_w: float | None = Field(default=None, description="Current power consumption")
    power_anomaly: bool = Field(default=False, description="Power consumption anomaly detected")
    issues: list[HealthIssue] = Field(default_factory=list, description="List of health issues")
    maintenance_recommendations: list[MaintenanceRecommendation] = Field(
        default_factory=list,
        description="Maintenance recommendations"
    )


class HealthSummary(BaseModel):
    """Overall health summary"""
    total_devices: int = Field(description="Total number of devices")
    healthy_devices: int = Field(description="Number of healthy devices")
    warning_devices: int = Field(description="Number of devices with warnings")
    error_devices: int = Field(description="Number of devices with errors")
    timestamp: str = Field(description="Summary timestamp")


class MaintenanceAlert(BaseModel):
    """Maintenance alert for a device"""
    device_id: str = Field(description="Device identifier")
    device_name: str = Field(description="Device name")
    issue_type: str = Field(description="Issue type")
    severity: HealthSeverity = Field(description="Severity level")
    message: str = Field(description="Alert message")
    timestamp: str = Field(description="Alert timestamp")

