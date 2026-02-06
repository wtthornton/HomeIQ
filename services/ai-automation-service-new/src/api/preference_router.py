"""
Preference API Router (Stub Implementation)

API endpoints for managing user suggestion preferences.
Returns default values until full implementation is added.

Epic AI-6 Story AI6.12: Frontend Preference Settings UI
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/preferences", tags=["Preferences"])


class PreferenceResponse(BaseModel):
    """Response model for user preferences."""

    max_suggestions: int = Field(..., description="Maximum suggestions to show (5-50)")
    creativity_level: str = Field(..., description="Creativity level (conservative/balanced/creative)")
    blueprint_preference: str = Field(..., description="Blueprint preference (low/medium/high)")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "max_suggestions": 10,
                "creativity_level": "balanced",
                "blueprint_preference": "medium"
            }]
        }
    }


class PreferenceUpdateRequest(BaseModel):
    """Request model for updating preferences."""

    max_suggestions: int | None = Field(None, ge=5, le=50, description="Maximum suggestions (5-50)")
    creativity_level: str | None = Field(None, description="Creativity level (conservative/balanced/creative)")
    blueprint_preference: str | None = Field(None, description="Blueprint preference (low/medium/high)")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "max_suggestions": 15,
                "creativity_level": "creative",
                "blueprint_preference": "high"
            }]
        }
    }


@router.get("", response_model=PreferenceResponse)
async def get_preferences(
    user_id: str = Query("default", description="User ID")
) -> PreferenceResponse:
    """
    Get current user preferences.
    
    Returns default preferences (stub implementation).
    Full implementation with database storage will be added in future update.
    """
    logger.info(f"Retrieving preferences for user '{user_id}' (stub - returning defaults)")
    
    # Return default values (stub implementation)
    return PreferenceResponse(
        max_suggestions=10,
        creativity_level="balanced",
        blueprint_preference="medium"
    )


@router.put("")
async def update_preferences(
    request: PreferenceUpdateRequest,
    user_id: str = Query("default", description="User ID")
):
    """
    Update user preferences.

    M10 fix: Returns 501 Not Implemented instead of silently ignoring the update.
    Full implementation with database storage will be added in a future update.
    """
    logger.info(f"Preference update requested for user '{user_id}' (not implemented)")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Preference storage is not yet implemented. Updates are not persisted."
    )
