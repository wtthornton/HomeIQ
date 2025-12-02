"""
Unit tests for PreferenceManager service.

Epic AI-6 Story AI6.7: User Preference Configuration System
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.blueprint_discovery.preference_manager import (
    PreferenceConfig,
    PreferenceManager,
)
from src.database.models import SuggestionPreference


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def preference_manager():
    """Create a PreferenceManager instance."""
    return PreferenceManager(user_id="test_user")


@pytest.mark.asyncio
async def test_get_max_suggestions_default(preference_manager):
    """Test getting default max_suggestions when not set."""
    with patch.object(preference_manager, '_get_preference', return_value=None):
        result = await preference_manager.get_max_suggestions()
        assert result == PreferenceConfig.DEFAULT_MAX_SUGGESTIONS


@pytest.mark.asyncio
async def test_get_max_suggestions_from_db(preference_manager):
    """Test getting max_suggestions from database."""
    with patch.object(preference_manager, '_get_preference', return_value="15"):
        result = await preference_manager.get_max_suggestions()
        assert result == 15


@pytest.mark.asyncio
async def test_get_max_suggestions_invalid_range(preference_manager):
    """Test getting max_suggestions with invalid range value."""
    with patch.object(preference_manager, '_get_preference', return_value="100"):
        result = await preference_manager.get_max_suggestions()
        # Should return default when out of range
        assert result == PreferenceConfig.DEFAULT_MAX_SUGGESTIONS


@pytest.mark.asyncio
async def test_get_max_suggestions_invalid_format(preference_manager):
    """Test getting max_suggestions with invalid format."""
    with patch.object(preference_manager, '_get_preference', return_value="not_a_number"):
        result = await preference_manager.get_max_suggestions()
        # Should return default when invalid format
        assert result == PreferenceConfig.DEFAULT_MAX_SUGGESTIONS


@pytest.mark.asyncio
async def test_get_creativity_level_default(preference_manager):
    """Test getting default creativity_level when not set."""
    with patch.object(preference_manager, '_get_preference', return_value=None):
        result = await preference_manager.get_creativity_level()
        assert result == PreferenceConfig.DEFAULT_CREATIVITY_LEVEL


@pytest.mark.asyncio
async def test_get_creativity_level_valid(preference_manager):
    """Test getting valid creativity_level."""
    with patch.object(preference_manager, '_get_preference', return_value="creative"):
        result = await preference_manager.get_creativity_level()
        assert result == "creative"


@pytest.mark.asyncio
async def test_get_creativity_level_case_insensitive(preference_manager):
    """Test creativity_level is case-insensitive."""
    with patch.object(preference_manager, '_get_preference', return_value="CREATIVE"):
        result = await preference_manager.get_creativity_level()
        assert result == "creative"


@pytest.mark.asyncio
async def test_get_creativity_level_invalid(preference_manager):
    """Test getting invalid creativity_level returns default."""
    with patch.object(preference_manager, '_get_preference', return_value="invalid"):
        result = await preference_manager.get_creativity_level()
        assert result == PreferenceConfig.DEFAULT_CREATIVITY_LEVEL


@pytest.mark.asyncio
async def test_get_blueprint_preference_default(preference_manager):
    """Test getting default blueprint_preference when not set."""
    with patch.object(preference_manager, '_get_preference', return_value=None):
        result = await preference_manager.get_blueprint_preference()
        assert result == PreferenceConfig.DEFAULT_BLUEPRINT_PREFERENCE


@pytest.mark.asyncio
async def test_get_blueprint_preference_valid(preference_manager):
    """Test getting valid blueprint_preference."""
    with patch.object(preference_manager, '_get_preference', return_value="high"):
        result = await preference_manager.get_blueprint_preference()
        assert result == "high"


@pytest.mark.asyncio
async def test_get_blueprint_preference_invalid(preference_manager):
    """Test getting invalid blueprint_preference returns default."""
    with patch.object(preference_manager, '_get_preference', return_value="invalid"):
        result = await preference_manager.get_blueprint_preference()
        assert result == PreferenceConfig.DEFAULT_BLUEPRINT_PREFERENCE


@pytest.mark.asyncio
async def test_update_max_suggestions_valid(preference_manager):
    """Test updating max_suggestions with valid value."""
    with patch.object(preference_manager, '_set_preference') as mock_set:
        await preference_manager.update_max_suggestions(20)
        mock_set.assert_called_once_with(PreferenceConfig.MAX_SUGGESTIONS_KEY, "20")


@pytest.mark.asyncio
async def test_update_max_suggestions_too_low(preference_manager):
    """Test updating max_suggestions with value too low."""
    with pytest.raises(ValueError, match="max_suggestions must be between"):
        await preference_manager.update_max_suggestions(3)


@pytest.mark.asyncio
async def test_update_max_suggestions_too_high(preference_manager):
    """Test updating max_suggestions with value too high."""
    with pytest.raises(ValueError, match="max_suggestions must be between"):
        await preference_manager.update_max_suggestions(100)


@pytest.mark.asyncio
async def test_update_creativity_level_valid(preference_manager):
    """Test updating creativity_level with valid value."""
    with patch.object(preference_manager, '_set_preference') as mock_set:
        await preference_manager.update_creativity_level("conservative")
        mock_set.assert_called_once_with(PreferenceConfig.CREATIVITY_LEVEL_KEY, "conservative")


@pytest.mark.asyncio
async def test_update_creativity_level_case_insensitive(preference_manager):
    """Test creativity_level update is case-insensitive."""
    with patch.object(preference_manager, '_set_preference') as mock_set:
        await preference_manager.update_creativity_level("CREATIVE")
        mock_set.assert_called_once_with(PreferenceConfig.CREATIVITY_LEVEL_KEY, "creative")


@pytest.mark.asyncio
async def test_update_creativity_level_invalid(preference_manager):
    """Test updating creativity_level with invalid value."""
    with pytest.raises(ValueError, match="creativity_level must be one of"):
        await preference_manager.update_creativity_level("invalid")


@pytest.mark.asyncio
async def test_update_blueprint_preference_valid(preference_manager):
    """Test updating blueprint_preference with valid value."""
    with patch.object(preference_manager, '_set_preference') as mock_set:
        await preference_manager.update_blueprint_preference("low")
        mock_set.assert_called_once_with(PreferenceConfig.BLUEPRINT_PREFERENCE_KEY, "low")


@pytest.mark.asyncio
async def test_update_blueprint_preference_invalid(preference_manager):
    """Test updating blueprint_preference with invalid value."""
    with pytest.raises(ValueError, match="blueprint_preference must be one of"):
        await preference_manager.update_blueprint_preference("invalid")


@pytest.mark.asyncio
async def test_update_preference_max_suggestions(preference_manager):
    """Test generic update_preference for max_suggestions."""
    with patch.object(preference_manager, 'update_max_suggestions') as mock_update:
        await preference_manager.update_preference(PreferenceConfig.MAX_SUGGESTIONS_KEY, "25")
        mock_update.assert_called_once_with(25)


@pytest.mark.asyncio
async def test_update_preference_creativity_level(preference_manager):
    """Test generic update_preference for creativity_level."""
    with patch.object(preference_manager, 'update_creativity_level') as mock_update:
        await preference_manager.update_preference(PreferenceConfig.CREATIVITY_LEVEL_KEY, "balanced")
        mock_update.assert_called_once_with("balanced")


@pytest.mark.asyncio
async def test_update_preference_blueprint_preference(preference_manager):
    """Test generic update_preference for blueprint_preference."""
    with patch.object(preference_manager, 'update_blueprint_preference') as mock_update:
        await preference_manager.update_preference(PreferenceConfig.BLUEPRINT_PREFERENCE_KEY, "high")
        mock_update.assert_called_once_with("high")


@pytest.mark.asyncio
async def test_update_preference_unknown_key(preference_manager):
    """Test generic update_preference with unknown key."""
    with pytest.raises(ValueError, match="Unknown preference key"):
        await preference_manager.update_preference("unknown_key", "value")


@pytest.mark.asyncio
async def test_get_all_preferences(preference_manager):
    """Test getting all preferences."""
    with patch.object(preference_manager, 'get_max_suggestions', return_value=15), \
         patch.object(preference_manager, 'get_creativity_level', return_value="creative"), \
         patch.object(preference_manager, 'get_blueprint_preference', return_value="high"):
        result = await preference_manager.get_all_preferences()
        
        assert result[PreferenceConfig.MAX_SUGGESTIONS_KEY] == 15
        assert result[PreferenceConfig.CREATIVITY_LEVEL_KEY] == "creative"
        assert result[PreferenceConfig.BLUEPRINT_PREFERENCE_KEY] == "high"


@pytest.mark.asyncio
async def test_get_preference_existing(preference_manager, mock_db_session):
    """Test _get_preference with existing preference."""
    mock_pref = SuggestionPreference(
        id=1,
        user_id="test_user",
        preference_key="max_suggestions",
        preference_value="20",
        updated_at=datetime.now(timezone.utc)
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_pref
    
    with patch('src.blueprint_discovery.preference_manager.get_db_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.execute.return_value = mock_result
        
        result = await preference_manager._get_preference("max_suggestions")
        assert result == "20"


@pytest.mark.asyncio
async def test_get_preference_missing(preference_manager, mock_db_session):
    """Test _get_preference with missing preference."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    
    with patch('src.blueprint_discovery.preference_manager.get_db_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.execute.return_value = mock_result
        
        result = await preference_manager._get_preference("max_suggestions")
        assert result is None


@pytest.mark.asyncio
async def test_get_preference_error(preference_manager, mock_db_session):
    """Test _get_preference handles errors gracefully."""
    with patch('src.blueprint_discovery.preference_manager.get_db_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.execute.side_effect = Exception("Database error")
        
        result = await preference_manager._get_preference("max_suggestions")
        assert result is None  # Should return None on error


@pytest.mark.asyncio
async def test_set_preference_update_existing(preference_manager, mock_db_session):
    """Test _set_preference updates existing preference."""
    existing_pref = SuggestionPreference(
        id=1,
        user_id="test_user",
        preference_key="max_suggestions",
        preference_value="10",
        updated_at=datetime.now(timezone.utc)
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_pref
    
    with patch('src.blueprint_discovery.preference_manager.get_db_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.execute.return_value = mock_result
        
        await preference_manager._set_preference("max_suggestions", "25")
        
        assert existing_pref.preference_value == "25"
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_set_preference_create_new(preference_manager, mock_db_session):
    """Test _set_preference creates new preference."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    
    with patch('src.blueprint_discovery.preference_manager.get_db_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.execute.return_value = mock_result
        
        await preference_manager._set_preference("max_suggestions", "25")
        
        mock_db_session.add.assert_called_once()
        added_pref = mock_db_session.add.call_args[0][0]
        assert isinstance(added_pref, SuggestionPreference)
        assert added_pref.user_id == "test_user"
        assert added_pref.preference_key == "max_suggestions"
        assert added_pref.preference_value == "25"
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_set_preference_error(preference_manager, mock_db_session):
    """Test _set_preference raises error on database failure."""
    with patch('src.blueprint_discovery.preference_manager.get_db_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await preference_manager._set_preference("max_suggestions", "25")


@pytest.mark.asyncio
async def test_preference_manager_custom_user_id():
    """Test PreferenceManager with custom user_id."""
    manager = PreferenceManager(user_id="custom_user")
    assert manager.user_id == "custom_user"
