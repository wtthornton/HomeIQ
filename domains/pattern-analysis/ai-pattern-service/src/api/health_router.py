"""
Health check router for Pattern Service

Epic 39, Story 39.5: Pattern Service Foundation

NOTE: The /health endpoint is now provided by StandardHealthCheck via
create_app (homeiq_resilience). This router provides supplementary
endpoints: /ready, /live, /database/integrity, /database/repair.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..database.integrity import (
    attempt_database_repair,
    check_database_integrity,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict[str, str]:
    """
    Readiness check endpoint.

    Indicates whether the service is ready to accept traffic.

    Returns:
        dict: Readiness status
    """
    return {"status": "ready"}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, str]:
    """
    Liveness check endpoint.

    Indicates whether the service is alive and running.

    Returns:
        dict: Liveness status
    """
    return {"status": "live"}


@router.get("/database/integrity", status_code=status.HTTP_200_OK)
async def check_database_integrity_endpoint(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Check database integrity.

    Returns database integrity status and health information.

    Args:
        db: Database session dependency

    Returns:
        dict: Integrity check results
    """
    try:
        is_healthy, error_msg = await check_database_integrity(db)

        if is_healthy:
            return {
                "status": "healthy",
                "database": "ok",
                "message": "Database integrity check passed"
            }
        else:
            return {
                "status": "unhealthy",
                "database": "corrupted",
                "message": "Database integrity check failed",
                "error": error_msg,
                "recommendation": "Run POST /health/database/repair to attempt repair"
            }
    except Exception as e:
        logger.error(f"Database integrity check endpoint failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check database integrity: {str(e)}"
        ) from e


@router.post("/database/repair", status_code=status.HTTP_200_OK)
async def repair_database_endpoint(
    x_internal_token: str = Header(..., alias="X-Internal-Token")
) -> dict[str, Any]:
    """
    Attempt to repair database corruption.

    **WARNING:** This operation may take several minutes and will create a backup.
    Only use this if database corruption is detected.
    Requires X-Internal-Token header for authentication.

    Returns:
        dict: Repair operation results
    """
    try:
        from pathlib import Path

        from ..config import settings

        if x_internal_token != settings.internal_api_token:
            raise HTTPException(status_code=403, detail="Forbidden")

        db_path = Path(settings.database_path)
        logger.info(f"Attempting database repair for: {db_path}")

        # Run repair (synchronous operation)
        repair_success = await attempt_database_repair(db_path)

        if repair_success:
            return {
                "status": "success",
                "message": "Database repair completed successfully",
                "recommendation": "Verify database integrity using GET /health/database/integrity"
            }
        else:
            return {
                "status": "failed",
                "message": "Database repair failed. Manual intervention may be required.",
                "recommendation": "Check logs for details and consider restoring from backup"
            }
    except Exception as e:
        logger.error(f"Database repair endpoint failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to repair database: {str(e)}"
        ) from e

