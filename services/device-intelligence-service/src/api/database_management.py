"""
Device Intelligence Service - Database Management API

API endpoints for database management and schema updates.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.database import recreate_tables
from ..config import Settings

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


@router.get("/")
async def database_management_info() -> Dict[str, Any]:
    """Get database management API information."""
    return {
        "message": "Database Management API",
        "endpoints": {
            "recreate_tables": "POST /api/database/recreate-tables - Recreate all tables (WARNING: Drops all data)",
            "status": "GET /api/database/status - Get database status"
        },
        "warnings": [
            "Recreating tables will DELETE ALL existing data",
            "Only use recreate_tables during development or schema migrations",
            "Make sure to backup data before recreating tables"
        ]
    }

