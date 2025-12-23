"""
Alias Management Router

Epic 39, Story 39.13: Router Modularization
Extracted from ask_ai_router.py for better organization.
Handles entity alias management endpoints.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...services.alias_service import AliasService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ask-ai/aliases", tags=["Alias Management"])


# Request/Response Models
class AliasCreateRequest(BaseModel):
    """Request model for creating an alias"""
    entity_id: str = Field(..., description="Entity ID to create alias for")
    alias: str = Field(..., description="Alias name (e.g., 'sleepy light')")
    user_id: str = Field(default="anonymous", description="User ID")


class AliasResponse(BaseModel):
    """Response model for alias operations"""
    entity_id: str
    alias: str
    user_id: str
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=AliasResponse, status_code=status.HTTP_201_CREATED)
async def create_alias(
    request: AliasCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new alias for an entity.
    
    Example:
        POST /api/v1/ask-ai/aliases
        {
            "entity_id": "light.bedroom_1",
            "alias": "sleepy light",
            "user_id": "user123"
        }
    """
    try:
        alias_service = AliasService(db)
        entity_alias = await alias_service.create_alias(
            entity_id=request.entity_id,
            alias=request.alias,
            user_id=request.user_id
        )

        if not entity_alias:
            raise HTTPException(
                status_code=400,
                detail=f"Alias '{request.alias}' already exists for user {request.user_id}"
            )

        return AliasResponse(
            entity_id=entity_alias.entity_id,
            alias=entity_alias.alias,
            user_id=entity_alias.user_id,
            created_at=entity_alias.created_at,
            updated_at=entity_alias.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alias: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{alias}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alias(
    alias: str,
    user_id: str = Query(default="anonymous", description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an alias.
    
    Args:
        alias: Alias to delete (URL-encoded)
        user_id: User ID (default: "anonymous")
    
    Example:
        DELETE /api/v1/ask-ai/aliases/sleepy%20light?user_id=user123
    """
    try:
        alias_service = AliasService(db)
        deleted = await alias_service.delete_alias(alias, user_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Alias '{alias}' not found for user {user_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alias: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=dict[str, list[str]])
async def list_aliases(
    user_id: str = Query(default="anonymous", description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all aliases for a user, grouped by entity_id.
    
    Returns a dictionary mapping entity_id -> list of aliases.
    
    Example:
        GET /api/v1/ask-ai/aliases?user_id=user123
        {
            "light.bedroom_1": ["sleepy light", "bedroom main"],
            "light.living_room_1": ["living room lamp"]
        }
    """
    try:
        alias_service = AliasService(db)
        aliases_by_entity = await alias_service.get_all_aliases(user_id)

        return aliases_by_entity
    except Exception as e:
        logger.error(f"Error listing aliases: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

