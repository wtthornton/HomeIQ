"""
Backup and restore router for data-retention service.
"""

from fastapi import APIRouter, HTTPException, Query, Request

from ..models import (
    BackupCreateRequest,
    BackupResponse,
    RestoreRequest,
    RestoreResponse,
    BackupHistoryResponse,
    BackupStatisticsResponse,
    CleanupBackupsRequest,
    CleanupBackupsResponse
)

router = APIRouter(prefix="/backup", tags=["backup"])


@router.post("", response_model=BackupResponse, status_code=201)
async def create_backup(request: Request, backup_request: BackupCreateRequest):
    """
    Create a backup.
    
    Creates a new backup with the specified configuration.
    """
    try:
        service = request.app.state.service
        backup_info = await service.create_backup(
            backup_type=backup_request.backup_type,
            include_data=backup_request.include_data,
            include_config=backup_request.include_config,
            include_logs=backup_request.include_logs
        )
        return backup_info
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/restore", response_model=RestoreResponse)
async def restore_backup(request: Request, restore_request: RestoreRequest):
    """
    Restore from a backup.
    
    Restores data, configuration, and/or logs from the specified backup.
    """
    try:
        service = request.app.state.service
        success = await service.restore_backup(
            backup_id=restore_request.backup_id,
            restore_data=restore_request.restore_data,
            restore_config=restore_request.restore_config,
            restore_logs=restore_request.restore_logs
        )

        if success:
            return {"message": "Backup restored successfully"}
        else:
            raise HTTPException(status_code=500, detail={"error": "Backup restore failed"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/backups", response_model=BackupHistoryResponse)
async def get_backup_history(
    request: Request,
    limit: int = Query(100, description="Maximum number of backups to return")
):
    """
    Get backup history.
    
    Returns a list of recent backups.
    """
    try:
        service = request.app.state.service
        history = service.get_backup_history(limit)
        return {"backups": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/stats", response_model=BackupStatisticsResponse)
async def get_backup_statistics(request: Request):
    """
    Get backup statistics.
    
    Returns statistics about backups including total count, size, and date range.
    """
    try:
        service = request.app.state.service
        stats = service.get_backup_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.delete("/cleanup", response_model=CleanupBackupsResponse)
async def cleanup_old_backups(
    request: Request,
    days_to_keep: int = Query(30, description="Number of days to keep backups")
):
    """
    Clean up old backup files.
    
    Deletes backup files older than the specified number of days.
    """
    try:
        service = request.app.state.service
        deleted_count = service.cleanup_old_backups(days_to_keep)
        return {
            "message": f"Cleaned up {deleted_count} old backup files",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

