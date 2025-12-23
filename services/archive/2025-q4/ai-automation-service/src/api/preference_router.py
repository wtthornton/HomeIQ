"""
Preference API Router

API endpoints for managing user suggestion preferences:
- max_suggestions (5-50)
- creativity_level (conservative/balanced/creative)
- blueprint_preference (low/medium/high)

Epic AI-6 Story AI6.12: Frontend Preference Settings UI
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..blueprint_discovery.preference_manager import PreferenceManager, PreferenceConfig
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/preferences", tags=["Preferences"])


class PreferenceResponse(BaseModel):
    """Response model for user preferences."""
    
    max_suggestions: int = Field(..., description="Maximum suggestions to show (5-50)")
    creativity_level: str = Field(..., description="Creativity level (conservative/balanced/creative)")
    blueprint_preference: str = Field(..., description="Blueprint preference (low/medium/high)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "max_suggestions": 10,
                "creativity_level": "balanced",
                "blueprint_preference": "medium"
            }
        }


class PreferenceUpdateRequest(BaseModel):
    """Request model for updating preferences."""
    
    max_suggestions: int | None = Field(None, ge=5, le=50, description="Maximum suggestions (5-50)")
    creativity_level: str | None = Field(None, description="Creativity level (conservative/balanced/creative)")
    blueprint_preference: str | None = Field(None, description="Blueprint preference (low/medium/high)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "max_suggestions": 15,
                "creativity_level": "creative",
                "blueprint_preference": "high"
            }
        }


@router.get("", response_model=PreferenceResponse)
async def get_preferences(
    user_id: str = Query("default", description="User ID"),
    db: AsyncSession = Depends(get_db)
) -> PreferenceResponse:
    """
    Get current user preferences.
    
    Returns the current preference values for the user.
    If preferences are not set, returns default values.
    """
    try:
        preference_manager = PreferenceManager(user_id=user_id)
        
        max_suggestions = await preference_manager.get_max_suggestions()
        creativity_level = await preference_manager.get_creativity_level()
        blueprint_preference = await preference_manager.get_blueprint_preference()
        
        logger.info(
            f"Retrieved preferences for user '{user_id}': "
            f"max_suggestions={max_suggestions}, "
            f"creativity_level={creativity_level}, "
            f"blueprint_preference={blueprint_preference}"
        )
        
        return PreferenceResponse(
            max_suggestions=max_suggestions,
            creativity_level=creativity_level,
            blueprint_preference=blueprint_preference
        )
        
    except Exception as e:
        logger.error(f"Failed to get preferences for user '{user_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve preferences: {str(e)}"
        ) from e


@router.put("", response_model=PreferenceResponse)
async def update_preferences(
    request: PreferenceUpdateRequest,
    user_id: str = Query("default", description="User ID"),
    db: AsyncSession = Depends(get_db)
) -> PreferenceResponse:
    """
    Update user preferences.
    
    Updates one or more preference values. Only provided values are updated.
    Validates all provided values before saving.
    """
    try:
        preference_manager = PreferenceManager(user_id=user_id)
        
        # Validate and update each provided preference
        if request.max_suggestions is not None:
            try:
                await preference_manager.update_preference("max_suggestions", str(request.max_suggestions))
                logger.info(f"Updated max_suggestions to {request.max_suggestions} for user '{user_id}'")
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid max_suggestions value: {str(e)}"
                ) from e
        
        if request.creativity_level is not None:
            try:
                await preference_manager.update_preference("creativity_level", request.creativity_level)
                logger.info(f"Updated creativity_level to {request.creativity_level} for user '{user_id}'")
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid creativity_level value: {str(e)}"
                ) from e
        
        if request.blueprint_preference is not None:
            try:
                await preference_manager.update_preference("blueprint_preference", request.blueprint_preference)
                logger.info(f"Updated blueprint_preference to {request.blueprint_preference} for user '{user_id}'")
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid blueprint_preference value: {str(e)}"
                ) from e
        
        # Return updated preferences
        max_suggestions = await preference_manager.get_max_suggestions()
        creativity_level = await preference_manager.get_creativity_level()
        blueprint_preference = await preference_manager.get_blueprint_preference()
        
        logger.info(
            f"Successfully updated preferences for user '{user_id}': "
            f"max_suggestions={max_suggestions}, "
            f"creativity_level={creativity_level}, "
            f"blueprint_preference={blueprint_preference}"
        )
        
        return PreferenceResponse(
            max_suggestions=max_suggestions,
            creativity_level=creativity_level,
            blueprint_preference=blueprint_preference
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update preferences for user '{user_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        ) from e
