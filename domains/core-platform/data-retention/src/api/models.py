"""
Pydantic models for data-retention API.
"""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    service_status: dict[str, Any]
    storage_metrics: dict[str, Any] | None = None
    active_alerts: int
    alerts: list[dict[str, Any]]


class StatisticsResponse(BaseModel):
    """Service statistics response model."""
    service_status: dict[str, Any]
    policy_statistics: dict[str, Any]
    cleanup_statistics: dict[str, Any] | None = None
    storage_statistics: dict[str, Any] | None = None
    compression_statistics: dict[str, Any] | None = None
    backup_statistics: dict[str, Any] | None = None


class RetentionPolicyModel(BaseModel):
    """Retention policy model."""
    name: str
    retention_period: int
    retention_unit: str = Field(default="days", description="Retention unit: days, weeks, months, years")
    enabled: bool = True
    description: str | None = None


class PolicyListResponse(BaseModel):
    """Policy list response model."""
    policies: list[dict[str, Any]]


class PolicyCreateRequest(BaseModel):
    """Request model for creating a retention policy."""
    name: str
    retention_period: int
    retention_unit: str = Field(default="days", description="Retention unit: days, weeks, months, years")
    enabled: bool = True
    description: str | None = None


class PolicyUpdateRequest(BaseModel):
    """Request model for updating a retention policy."""
    name: str  # Required for update
    retention_period: int | None = None
    retention_unit: str | None = None
    enabled: bool | None = None
    description: str | None = None


class PolicyResponse(BaseModel):
    """Policy operation response model."""
    message: str


class CleanupRequest(BaseModel):
    """Request model for cleanup operation."""
    policy_name: str | None = None


class CleanupResponse(BaseModel):
    """Cleanup operation response model."""
    results: list[dict[str, Any]]


class BackupCreateRequest(BaseModel):
    """Request model for creating a backup."""
    backup_type: str = Field(default="full", description="Type of backup: full, incremental")
    include_data: bool = Field(default=True, description="Include data in backup")
    include_config: bool = Field(default=True, description="Include configuration in backup")
    include_logs: bool = Field(default=False, description="Include logs in backup")


class BackupInfo(BaseModel):
    """Backup information model."""
    backup_id: str
    backup_type: str
    created_at: str
    size_bytes: int
    status: str


class BackupResponse(BaseModel):
    """Backup creation response model."""
    backup_id: str
    backup_type: str
    created_at: str
    size_bytes: int
    status: str


class RestoreRequest(BaseModel):
    """Request model for restoring from backup."""
    backup_id: str
    restore_data: bool = Field(default=True, description="Restore data")
    restore_config: bool = Field(default=True, description="Restore configuration")
    restore_logs: bool = Field(default=False, description="Restore logs")


class RestoreResponse(BaseModel):
    """Restore operation response model."""
    message: str


class BackupHistoryResponse(BaseModel):
    """Backup history response model."""
    backups: list[dict[str, Any]]


class BackupStatisticsResponse(BaseModel):
    """Backup statistics response model."""
    total_backups: int
    total_size_bytes: int
    oldest_backup: str | None = None
    newest_backup: str | None = None


class CleanupBackupsRequest(BaseModel):
    """Request model for cleaning up old backups."""
    days_to_keep: int = Field(default=30, description="Number of days to keep backups")


class CleanupBackupsResponse(BaseModel):
    """Cleanup backups response model."""
    message: str
    deleted_count: int


class RetentionStatsResponse(BaseModel):
    """Retention statistics response model."""
    metrics: dict[str, Any]


class RetentionOperationResponse(BaseModel):
    """Retention operation response model."""
    success: bool
    message: str | None = None
    result: dict[str, Any] | None = None

