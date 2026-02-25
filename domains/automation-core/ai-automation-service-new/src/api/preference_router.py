"""
Preference API Router

API endpoints for managing user suggestion preferences.
Preferences are stored in the database and retrieved per user_id.

Epic AI-6 Story AI6.12: Frontend Preference Settings UI
"""

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from ..api.dependencies import DatabaseSession
from ..database.models import UserPreferences

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/preferences", tags=["Preferences"])

# --- Constants ---

VALID_CREATIVITY_LEVELS = ("conservative", "balanced", "creative")
VALID_BLUEPRINT_PREFERENCES = ("none", "low", "medium", "high")

DEFAULT_MAX_SUGGESTIONS = 10
DEFAULT_CREATIVITY_LEVEL = "balanced"
DEFAULT_BLUEPRINT_PREFERENCE = "medium"


# --- Pydantic Models ---


class PreferenceResponse(BaseModel):
    """Response model for user preferences."""

    max_suggestions: int = Field(..., description="Maximum suggestions to show (5-50)")
    creativity_level: str = Field(
        ..., description="Creativity level (conservative/balanced/creative)"
    )
    blueprint_preference: str = Field(
        ..., description="Blueprint preference (none/low/medium/high)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "max_suggestions": 10,
                    "creativity_level": "balanced",
                    "blueprint_preference": "medium",
                }
            ]
        }
    }


class PreferenceUpdateRequest(BaseModel):
    """Request model for updating preferences."""

    max_suggestions: int | None = Field(None, ge=5, le=50, description="Maximum suggestions (5-50)")
    creativity_level: str | None = Field(
        None, description="Creativity level (conservative/balanced/creative)"
    )
    blueprint_preference: str | None = Field(
        None, description="Blueprint preference (none/low/medium/high)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "max_suggestions": 15,
                    "creativity_level": "creative",
                    "blueprint_preference": "high",
                }
            ]
        }
    }

    @field_validator("creativity_level")
    @classmethod
    def validate_creativity_level(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_CREATIVITY_LEVELS:
            raise ValueError(
                f"creativity_level must be one of {VALID_CREATIVITY_LEVELS}, got '{v}'"
            )
        return v

    @field_validator("blueprint_preference")
    @classmethod
    def validate_blueprint_preference(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_BLUEPRINT_PREFERENCES:
            raise ValueError(
                f"blueprint_preference must be one of {VALID_BLUEPRINT_PREFERENCES}, got '{v}'"
            )
        return v


# --- Endpoints ---


@router.get("", response_model=PreferenceResponse)
async def get_preferences(
    db: DatabaseSession,
    user_id: str = Query("default", description="User ID"),
) -> PreferenceResponse:
    """
    Get current user preferences.

    Queries the database for the given user_id. If no record exists,
    returns hardcoded defaults without creating a database record
    (lazy creation on first PUT).
    """
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()

    if prefs is None:
        logger.info("No preferences found for user '%s', returning defaults", user_id)
        return PreferenceResponse(
            max_suggestions=DEFAULT_MAX_SUGGESTIONS,
            creativity_level=DEFAULT_CREATIVITY_LEVEL,
            blueprint_preference=DEFAULT_BLUEPRINT_PREFERENCE,
        )

    logger.info("Returning stored preferences for user '%s'", user_id)
    return PreferenceResponse(
        max_suggestions=prefs.max_suggestions,
        creativity_level=prefs.creativity_level,
        blueprint_preference=prefs.blueprint_preference,
    )


@router.put("", response_model=PreferenceResponse)
async def update_preferences(
    request: PreferenceUpdateRequest,
    db: DatabaseSession,
    user_id: str = Query("default", description="User ID"),
) -> PreferenceResponse:
    """
    Update user preferences.

    Upserts the user preferences record: creates if the user has no stored
    preferences, or updates the existing record with the provided fields.
    Only fields included in the request body are updated; omitted fields
    retain their current (or default) values.
    """
    # Check for existing record
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()

    if prefs is None:
        # Create new record with defaults, then overlay request fields
        prefs = UserPreferences(
            user_id=user_id,
            max_suggestions=DEFAULT_MAX_SUGGESTIONS,
            creativity_level=DEFAULT_CREATIVITY_LEVEL,
            blueprint_preference=DEFAULT_BLUEPRINT_PREFERENCE,
        )
        db.add(prefs)
        logger.info("Creating new preferences record for user '%s'", user_id)

    # Apply only the fields that were explicitly provided
    if request.max_suggestions is not None:
        prefs.max_suggestions = request.max_suggestions
    if request.creativity_level is not None:
        prefs.creativity_level = request.creativity_level
    if request.blueprint_preference is not None:
        prefs.blueprint_preference = request.blueprint_preference

    await db.commit()
    await db.refresh(prefs)

    logger.info("Updated preferences for user '%s'", user_id)
    return PreferenceResponse(
        max_suggestions=prefs.max_suggestions,
        creativity_level=prefs.creativity_level,
        blueprint_preference=prefs.blueprint_preference,
    )
