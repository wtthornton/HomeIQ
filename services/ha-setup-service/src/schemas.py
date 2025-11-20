"""Pydantic schemas for API validation (Context7 best practice)"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status enum"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class IntegrationStatus(str, Enum):
    """Integration status enum"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"


# Environment Health Schemas

class IntegrationHealthDetail(BaseModel):
    """Individual integration health status"""
    name: str
    type: str
    status: IntegrationStatus
    is_configured: bool
    is_connected: bool
    error_message: str | None = None
    check_details: dict[str, Any] | None = None
    last_check: datetime | None = None


class PerformanceMetrics(BaseModel):
    """Performance metrics"""
    response_time_ms: float = Field(..., description="Average response time in milliseconds")
    cpu_usage_percent: float | None = Field(None, description="CPU usage percentage")
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")
    uptime_seconds: int | None = Field(None, description="System uptime in seconds")


class EnvironmentHealthResponse(BaseModel):
    """Environment health response model"""
    health_score: int = Field(..., ge=0, le=100, description="Overall health score (0-100)")
    ha_status: HealthStatus
    ha_version: str | None = None
    integrations: list[IntegrationHealthDetail]
    performance: PerformanceMetrics
    issues_detected: list[str] = Field(default_factory=list)
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "health_score": 85,
                "ha_status": "healthy",
                "ha_version": "2025.1.0",
                "integrations": [
                    {
                        "name": "MQTT",
                        "type": "mqtt",
                        "status": "healthy",
                        "is_configured": True,
                        "is_connected": True,
                        "error_message": None,
                        "last_check": "2025-01-18T15:30:00Z"
                    }
                ],
                "performance": {
                    "response_time_ms": 45.2,
                    "cpu_usage_percent": 12.5,
                    "memory_usage_mb": 256.0,
                    "uptime_seconds": 86400
                },
                "issues_detected": [],
                "timestamp": "2025-01-18T15:30:00Z"
            }
        }


# Integration Health Schemas

class IntegrationHealthCreate(BaseModel):
    """Create integration health record"""
    integration_name: str
    integration_type: str
    status: IntegrationStatus
    is_configured: bool = False
    is_connected: bool = False
    error_message: str | None = None
    check_details: dict | None = None


class IntegrationHealthResponse(BaseModel):
    """Integration health response"""
    id: int
    integration_name: str
    integration_type: str
    status: IntegrationStatus
    is_configured: bool
    is_connected: bool
    error_message: str | None
    last_check: datetime
    timestamp: datetime

    class Config:
        from_attributes = True


# Performance Metric Schemas

class PerformanceMetricCreate(BaseModel):
    """Create performance metric"""
    metric_type: str
    metric_value: float
    component: str | None = None
    metric_metadata: dict | None = None  # Renamed from 'metadata' to match model


class PerformanceMetricResponse(BaseModel):
    """Performance metric response"""
    id: int
    timestamp: datetime
    metric_type: str
    metric_value: float
    component: str | None
    metric_metadata: dict | None  # Renamed from 'metadata' to match model

    class Config:
        from_attributes = True


# Setup Wizard Schemas

class SetupWizardStatus(str, Enum):
    """Setup wizard status enum"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SetupWizardSessionCreate(BaseModel):
    """Create setup wizard session"""
    integration_type: str
    total_steps: int
    configuration: dict | None = None


class SetupWizardSessionResponse(BaseModel):
    """Setup wizard session response"""
    session_id: str
    integration_type: str
    status: SetupWizardStatus
    steps_completed: int
    total_steps: int
    current_step: str | None
    configuration: dict | None
    error_log: list[dict] | None
    created_at: datetime
    updated_at: datetime | None
    completed_at: datetime | None

    class Config:
        from_attributes = True


# Health Check Response (Simple)

class HealthCheckResponse(BaseModel):
    """Simple health check response"""
    status: str
    service: str
    timestamp: datetime
    version: str = "1.0.0"


# Bridge Management Schemas

class RecoveryAttemptResponse(BaseModel):
    """Recovery attempt response"""
    timestamp: datetime
    action: str
    success: bool
    error_message: str | None = None
    duration_seconds: float | None = None


class BridgeHealthResponse(BaseModel):
    """Bridge health status response"""
    bridge_state: str
    is_connected: bool
    health_score: float = Field(ge=0, le=100)
    device_count: int
    response_time_ms: float
    signal_strength_avg: float | None = None
    network_health_score: float | None = None
    consecutive_failures: int
    recommendations: list[str] = Field(default_factory=list)
    last_check: datetime
    recovery_attempts: list[RecoveryAttemptResponse] = Field(default_factory=list)


class RecoveryRequest(BaseModel):
    """Recovery request"""
    force: bool = Field(False, description="Force recovery even if cooldown active")


class RecoveryResponse(BaseModel):
    """Recovery response"""
    success: bool
    message: str
    timestamp: datetime
