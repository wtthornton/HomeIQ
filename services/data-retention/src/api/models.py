"""
Pydantic models for data-retention API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    service_status: Dict[str, Any]
    storage_metrics: Optional[Dict[str, Any]] = None
    active_alerts: int
    alerts: List[Dict[str, Any]]


class StatisticsResponse(BaseModel):
    """Service statistics response model."""
    service_status: Dict[str, Any]
    policy_statistics: Dict[str, Any]
    cleanup_statistics: Optional[Dict[str, Any]] = None
    storage_statistics: Optional[Dict[str, Any]] = None
    compression_statistics: Optional[Dict[str, Any]] = None
    backup_statistics: Optional[Dict[str, Any]] = None


class RetentionPolicyModel(BaseModel):
    """Retention policy model."""
    name: str
    retention_period: int
    retention_unit: str = Field(default="days", description="Retention unit: days, weeks, months, years")
    enabled: bool = True
    description: Optional[str] = None


class PolicyListResponse(BaseModel):
    """Policy list response model."""
    policies: List[Dict[str, Any]]


class PolicyCreateRequest(BaseModel):
    """Request model for creating a retention policy."""
    name: str
    retention_period: int
    retention_unit: str = Field(default="days", description="Retention unit: days, weeks, months, years")
    enabled: bool = True
    description: Optional[str] = None


class PolicyUpdateRequest(BaseModel):
    """Request model for updating a retention policy."""
    name: str  # Required for update
    retention_period: Optional[int] = None
    retention_unit: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


class PolicyResponse(BaseModel):
    """Policy operation response model."""
    message: str


class CleanupRequest(BaseModel):
    """Request model for cleanup operation."""
    policy_name: Optional[str] = None


class CleanupResponse(BaseModel):
    """Cleanup operation response model."""
    results: List[Dict[str, Any]]


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
    backups: List[Dict[str, Any]]


class BackupStatisticsResponse(BaseModel):
    """Backup statistics response model."""
    total_backups: int
    total_size_bytes: int
    oldest_backup: Optional[str] = None
    newest_backup: Optional[str] = None


class CleanupBackupsRequest(BaseModel):
    """Request model for cleaning up old backups."""
    days_to_keep: int = Field(default=30, description="Number of days to keep backups")


class CleanupBackupsResponse(BaseModel):
    """Cleanup backups response model."""
    message: str
    deleted_count: int


class RetentionStatsResponse(BaseModel):
    """Retention statistics response model."""
    metrics: Dict[str, Any]


class RetentionOperationResponse(BaseModel):
    """Retention operation response model."""
    success: bool
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

