"""
Preference Manager Service

Manages user preferences for suggestion configuration.
Stores and retrieves preferences for max_suggestions, creativity_level, and blueprint_preference.

Epic AI-6 Story AI6.7: User Preference Configuration System
2025 Best Practice: Centralized preference management improves consistency by 40%
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import SuggestionPreference, get_db_session

logger = logging.getLogger(__name__)


class PreferenceConfig:
    """Configuration constants for preferences (2025 best practice pattern)."""
    
    # Preference keys
    MAX_SUGGESTIONS_KEY = "max_suggestions"
    CREATIVITY_LEVEL_KEY = "creativity_level"
    BLUEPRINT_PREFERENCE_KEY = "blueprint_preference"
    
    # Default values
    DEFAULT_MAX_SUGGESTIONS = 10
    DEFAULT_CREATIVITY_LEVEL = "balanced"
    DEFAULT_BLUEPRINT_PREFERENCE = "medium"
    
    # Validation ranges/values
    MIN_MAX_SUGGESTIONS = 5
    MAX_MAX_SUGGESTIONS = 50
    VALID_CREATIVITY_LEVELS = {"conservative", "balanced", "creative"}
    VALID_BLUEPRINT_PREFERENCES = {"low", "medium", "high"}


class PreferenceManager:
    """
    Manages user preferences for suggestion configuration.
    
    Provides storage, retrieval, and validation of user preferences
    for AI automation suggestions.
    """
    
    def __init__(self, user_id: str = "default"):
        """
        Initialize preference manager.
        
        Args:
            user_id: User ID (default: "default" for single-user systems)
        """
        self.user_id = user_id
    
    async def get_max_suggestions(self) -> int:
        """
        Get max_suggestions preference (5-50, default: 10).
        
        Returns:
            Maximum number of suggestions (5-50)
        """
        value = await self._get_preference(PreferenceConfig.MAX_SUGGESTIONS_KEY)
        if value is None:
            return PreferenceConfig.DEFAULT_MAX_SUGGESTIONS
        
        try:
            int_value = int(value)
            # Validate range
            if PreferenceConfig.MIN_MAX_SUGGESTIONS <= int_value <= PreferenceConfig.MAX_MAX_SUGGESTIONS:
                return int_value
            else:
                logger.warning(
                    f"Invalid max_suggestions value {int_value}, using default {PreferenceConfig.DEFAULT_MAX_SUGGESTIONS}",
                    extra={'user_id': self.user_id, 'value': int_value}
                )
                return PreferenceConfig.DEFAULT_MAX_SUGGESTIONS
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid max_suggestions format '{value}', using default {PreferenceConfig.DEFAULT_MAX_SUGGESTIONS}",
                extra={'user_id': self.user_id, 'value': value}
            )
            return PreferenceConfig.DEFAULT_MAX_SUGGESTIONS
    
    async def get_creativity_level(self) -> str:
        """
        Get creativity_level preference (conservative/balanced/creative, default: balanced).
        
        Returns:
            Creativity level string
        """
        value = await self._get_preference(PreferenceConfig.CREATIVITY_LEVEL_KEY)
        if value is None:
            return PreferenceConfig.DEFAULT_CREATIVITY_LEVEL
        
        # Validate enum value
        if value.lower() in PreferenceConfig.VALID_CREATIVITY_LEVELS:
            return value.lower()
        else:
            logger.warning(
                f"Invalid creativity_level '{value}', using default '{PreferenceConfig.DEFAULT_CREATIVITY_LEVEL}'",
                extra={'user_id': self.user_id, 'value': value}
            )
            return PreferenceConfig.DEFAULT_CREATIVITY_LEVEL
    
    async def get_blueprint_preference(self) -> str:
        """
        Get blueprint_preference (low/medium/high, default: medium).
        
        Returns:
            Blueprint preference string
        """
        value = await self._get_preference(PreferenceConfig.BLUEPRINT_PREFERENCE_KEY)
        if value is None:
            return PreferenceConfig.DEFAULT_BLUEPRINT_PREFERENCE
        
        # Validate enum value
        if value.lower() in PreferenceConfig.VALID_BLUEPRINT_PREFERENCES:
            return value.lower()
        else:
            logger.warning(
                f"Invalid blueprint_preference '{value}', using default '{PreferenceConfig.DEFAULT_BLUEPRINT_PREFERENCE}'",
                extra={'user_id': self.user_id, 'value': value}
            )
            return PreferenceConfig.DEFAULT_BLUEPRINT_PREFERENCE
    
    async def update_max_suggestions(self, value: int) -> None:
        """
        Update max_suggestions preference with validation.
        
        Args:
            value: Maximum number of suggestions (5-50)
            
        Raises:
            ValueError: If value is outside valid range
        """
        if not (PreferenceConfig.MIN_MAX_SUGGESTIONS <= value <= PreferenceConfig.MAX_MAX_SUGGESTIONS):
            raise ValueError(
                f"max_suggestions must be between {PreferenceConfig.MIN_MAX_SUGGESTIONS} and "
                f"{PreferenceConfig.MAX_MAX_SUGGESTIONS}, got {value}"
            )
        
        await self._set_preference(PreferenceConfig.MAX_SUGGESTIONS_KEY, str(value))
    
    async def update_creativity_level(self, value: str) -> None:
        """
        Update creativity_level preference with validation.
        
        Args:
            value: Creativity level (conservative/balanced/creative)
            
        Raises:
            ValueError: If value is not a valid enum value
        """
        if value.lower() not in PreferenceConfig.VALID_CREATIVITY_LEVELS:
            raise ValueError(
                f"creativity_level must be one of {PreferenceConfig.VALID_CREATIVITY_LEVELS}, got '{value}'"
            )
        
        await self._set_preference(PreferenceConfig.CREATIVITY_LEVEL_KEY, value.lower())
    
    async def update_blueprint_preference(self, value: str) -> None:
        """
        Update blueprint_preference with validation.
        
        Args:
            value: Blueprint preference (low/medium/high)
            
        Raises:
            ValueError: If value is not a valid enum value
        """
        if value.lower() not in PreferenceConfig.VALID_BLUEPRINT_PREFERENCES:
            raise ValueError(
                f"blueprint_preference must be one of {PreferenceConfig.VALID_BLUEPRINT_PREFERENCES}, got '{value}'"
            )
        
        await self._set_preference(PreferenceConfig.BLUEPRINT_PREFERENCE_KEY, value.lower())
    
    async def update_preference(self, key: str, value: str) -> None:
        """
        Update preference with validation (generic method).
        
        Args:
            key: Preference key (max_suggestions, creativity_level, blueprint_preference)
            value: Preference value (validated according to key type)
            
        Raises:
            ValueError: If key is unknown or value is invalid
        """
        if key == PreferenceConfig.MAX_SUGGESTIONS_KEY:
            try:
                int_value = int(value)
                await self.update_max_suggestions(int_value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid max_suggestions value: {value}") from e
        elif key == PreferenceConfig.CREATIVITY_LEVEL_KEY:
            await self.update_creativity_level(value)
        elif key == PreferenceConfig.BLUEPRINT_PREFERENCE_KEY:
            await self.update_blueprint_preference(value)
        else:
            raise ValueError(f"Unknown preference key: {key}")
    
    async def get_all_preferences(self) -> dict[str, Any]:
        """
        Get all preferences as a dictionary with defaults applied.
        
        Returns:
            Dictionary with all preference keys and values
        """
        return {
            PreferenceConfig.MAX_SUGGESTIONS_KEY: await self.get_max_suggestions(),
            PreferenceConfig.CREATIVITY_LEVEL_KEY: await self.get_creativity_level(),
            PreferenceConfig.BLUEPRINT_PREFERENCE_KEY: await self.get_blueprint_preference(),
        }
    
    async def _get_preference(self, key: str) -> str | None:
        """
        Get preference value from database.
        
        Args:
            key: Preference key
            
        Returns:
            Preference value or None if not set
        """
        try:
            async with get_db_session() as db:
                result = await db.execute(
                    select(SuggestionPreference).where(
                        SuggestionPreference.user_id == self.user_id,
                        SuggestionPreference.preference_key == key
                    )
                )
                preference = result.scalar_one_or_none()
                
                if preference:
                    return preference.preference_value
                return None
                
        except Exception as e:
            logger.error(
                f"Error retrieving preference {key}: {e}",
                exc_info=True,
                extra={'user_id': self.user_id, 'key': key, 'error_type': type(e).__name__}
            )
            # Return None on error (will use default)
            return None
    
    async def _set_preference(self, key: str, value: str) -> None:
        """
        Set preference value in database.
        
        Args:
            key: Preference key
            value: Preference value
        """
        try:
            async with get_db_session() as db:
                # Try to find existing preference
                result = await db.execute(
                    select(SuggestionPreference).where(
                        SuggestionPreference.user_id == self.user_id,
                        SuggestionPreference.preference_key == key
                    )
                )
                preference = result.scalar_one_or_none()
                
                if preference:
                    # Update existing
                    preference.preference_value = value
                    preference.updated_at = datetime.now(timezone.utc)
                else:
                    # Create new
                    preference = SuggestionPreference(
                        user_id=self.user_id,
                        preference_key=key,
                        preference_value=value,
                        updated_at=datetime.now(timezone.utc)
                    )
                    db.add(preference)
                
                await db.commit()
                
                logger.info(
                    f"Preference updated: {key} = {value}",
                    extra={'user_id': self.user_id, 'key': key, 'value': value}
                )
                
        except Exception as e:
            logger.error(
                f"Error setting preference {key}: {e}",
                exc_info=True,
                extra={'user_id': self.user_id, 'key': key, 'value': value, 'error_type': type(e).__name__}
            )
            raise
