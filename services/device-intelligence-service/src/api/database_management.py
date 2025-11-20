"""
Device Intelligence Service - Database Management API

API endpoints for database management and schema updates.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..core.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/database", tags=["Database Management"])

settings = Settings()


class RecreateTablesResponse(BaseModel):
    """Response for table recreation."""
    success: bool
    message: str


class DatabaseStatusResponse(BaseModel):
    """Database status response."""
    status: str
    message: str


class DatabaseCleanupResponse(BaseModel):
    """Response for database cleanup."""
    success: bool
    message: str
    records_deleted: int


class DatabaseOptimizeResponse(BaseModel):
    """Response for database optimization."""
    success: bool
    message: str


class DatabaseStatsResponse(BaseModel):
    """Database statistics response."""
    database_size_mb: float
    table_count: int
    total_records: int
    tables: dict[str, int]


@router.post("/recreate-tables", response_model=RecreateTablesResponse)
async def recreate_database_tables() -> RecreateTablesResponse:
    """
    Recreate all database tables with the latest schema.
    
    **WARNING:** This will drop all existing data and recreate tables.
    Only use this during development or when you need to apply schema changes.
    
    Returns:
        RecreateTablesResponse: Success status and message
    """
    try:
        logger.info("🔄 Recreating database tables")

        # Import here to avoid circular dependencies
        from ..core.database import recreate_tables

        await recreate_tables()

        logger.info("✅ Database tables recreated successfully")
        return RecreateTablesResponse(
            success=True,
            message="Database tables recreated successfully with latest schema"
        )

    except Exception as e:
        logger.error(f"❌ Failed to recreate database tables: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to recreate database tables: {str(e)}"
        )


@router.get("/status", response_model=DatabaseStatusResponse)
async def get_database_status() -> DatabaseStatusResponse:
    """
    Get database status and connection information.
    
    Returns:
        DatabaseStatusResponse: Database status information
    """
    try:
        # Import here to avoid circular dependencies
        from ..core.database import _engine

        if _engine is None:
            return DatabaseStatusResponse(
                status="not_initialized",
                message="Database not initialized"
            )

        # Try to execute a simple query to verify connection
        from sqlalchemy import text
        async with _engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()

        return DatabaseStatusResponse(
            status="connected",
            message="Database connection is active"
        )

    except Exception as e:
        logger.error(f"❌ Database status check failed: {e}")
        return DatabaseStatusResponse(
            status="error",
            message=f"Database error: {str(e)}"
        )


@router.post("/cleanup", response_model=DatabaseCleanupResponse)
async def cleanup_database(
    days_to_keep: int = 90,
    session: AsyncSession = Depends(get_db_session)
) -> DatabaseCleanupResponse:
    """
    Clean up old records from the database.
    
    Args:
        days_to_keep: Number of days of data to keep (default: 90)
    
    Returns:
        DatabaseCleanupResponse: Cleanup results
    """
    try:
        logger.info(f"🧹 Starting database cleanup (keeping {days_to_keep} days)")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        records_deleted = 0

        # Clean up old predictions
        result = await session.execute(
            text("DELETE FROM predictions WHERE predicted_at < :cutoff"),
            {"cutoff": cutoff_date}
        )
        records_deleted += result.rowcount

        # Clean up old recommendations
        result = await session.execute(
            text("DELETE FROM recommendations WHERE created_at < :cutoff AND status = 'rejected'"),
            {"cutoff": cutoff_date}
        )
        records_deleted += result.rowcount

        await session.commit()

        logger.info(f"✅ Database cleanup completed: {records_deleted} records deleted")
        return DatabaseCleanupResponse(
            success=True,
            message="Database cleanup completed successfully",
            records_deleted=records_deleted
        )

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Database cleanup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database cleanup failed: {str(e)}"
        )


@router.post("/optimize", response_model=DatabaseOptimizeResponse)
async def optimize_database(
    session: AsyncSession = Depends(get_db_session)
) -> DatabaseOptimizeResponse:
    """
    Optimize database by running VACUUM and ANALYZE.
    
    Returns:
        DatabaseOptimizeResponse: Optimization results
    """
    try:
        logger.info("🔧 Starting database optimization")

        # Run VACUUM to reclaim space
        await session.execute(text("VACUUM"))

        # Run ANALYZE to update statistics
        await session.execute(text("ANALYZE"))

        await session.commit()

        logger.info("✅ Database optimization completed")
        return DatabaseOptimizeResponse(
            success=True,
            message="Database optimized successfully (VACUUM and ANALYZE completed)"
        )

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Database optimization failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database optimization failed: {str(e)}"
        )


@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_database_stats(
    session: AsyncSession = Depends(get_db_session)
) -> DatabaseStatsResponse:
    """
    Get database statistics including size and record counts.
    
    Returns:
        DatabaseStatsResponse: Database statistics
    """
    try:
        # Get database file size
        db_url = settings.get_database_url()
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                db_size_bytes = os.path.getsize(db_path)
                db_size_mb = db_size_bytes / (1024 * 1024)
            else:
                db_size_mb = 0.0
        else:
            db_size_mb = 0.0

        # Get table names and record counts
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        )
        tables = [row[0] for row in result.fetchall()]

        table_counts = {}
        total_records = 0

        for table in tables:
            try:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                table_counts[table] = count
                total_records += count
            except Exception as e:
                logger.warning(f"Could not get count for table {table}: {e}")
                table_counts[table] = 0

        return DatabaseStatsResponse(
            database_size_mb=round(db_size_mb, 2),
            table_count=len(tables),
            total_records=total_records,
            tables=table_counts
        )

    except Exception as e:
        logger.error(f"❌ Failed to get database stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database stats: {str(e)}"
        )


@router.get("/")
async def database_management_info() -> dict[str, Any]:
    """Get database management API information."""
    return {
        "message": "Database Management API",
        "endpoints": {
            "recreate_tables": "POST /api/database/recreate-tables - Recreate all tables (WARNING: Drops all data)",
            "status": "GET /api/database/status - Get database status",
            "cleanup": "POST /api/database/cleanup - Clean up old records",
            "optimize": "POST /api/database/optimize - Optimize database (VACUUM, ANALYZE)",
            "stats": "GET /api/database/stats - Get database statistics"
        },
        "warnings": [
            "Recreating tables will DELETE ALL existing data",
            "Only use recreate_tables during development or schema migrations",
            "Make sure to backup data before recreating tables"
        ]
    }

