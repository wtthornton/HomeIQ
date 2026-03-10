"""Tests for backup router response shape (BackupInfo -> BackupResponse mapping, Epic 46)."""

from datetime import UTC, datetime

import pytest

from src.api.models import BackupResponse
from src.backup_restore import BackupInfo


def _backup_info_to_response(backup_info: BackupInfo) -> BackupResponse:
    """Replicate the mapping logic from backup router (create_backup endpoint)."""
    created_at = backup_info.created_at
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    return BackupResponse(
        backup_id=backup_info.backup_id,
        backup_type=backup_info.backup_type,
        created_at=created_at,
        size_bytes=backup_info.size_bytes,
        status="success" if backup_info.success else "failed",
    )


def test_backup_response_shape_success():
    """BackupInfo with success=True maps to BackupResponse with status 'success' and created_at string."""
    now = datetime.now(UTC)
    backup_info = BackupInfo(
        backup_id="full_20260101_120000",
        backup_type="full",
        created_at=now,
        size_bytes=1024,
        file_path="/backups/full_20260101_120000.tar.gz",
        metadata={},
        success=True,
    )
    response = _backup_info_to_response(backup_info)

    assert response.backup_id == "full_20260101_120000"
    assert response.backup_type == "full"
    assert response.size_bytes == 1024
    assert response.status == "success"
    assert isinstance(response.created_at, str)
    assert now.isoformat() in response.created_at or response.created_at.startswith("202")


def test_backup_response_status_failed():
    """BackupInfo with success=False maps to BackupResponse with status 'failed'."""
    now = datetime.now(UTC)
    backup_info = BackupInfo(
        backup_id="full_20260101_120001",
        backup_type="full",
        created_at=now,
        size_bytes=0,
        file_path="",
        metadata={},
        success=False,
        error_message="Backup failed",
    )
    response = _backup_info_to_response(backup_info)

    assert response.status == "failed"
    assert response.backup_id == "full_20260101_120001"
    assert response.size_bytes == 0
    assert isinstance(response.created_at, str)
