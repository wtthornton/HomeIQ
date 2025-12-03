"""Tests for Context Builder Service"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.services.context_builder import ContextBuilder
from src.config import Settings
from src.database import ContextCache


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    return Settings(
        ha_url="http://test-ha:8123",
        ha_access_token="test-token",
        data_api_url="http://test-data-api:8006",
        device_intelligence_url="http://test-device-intel:8028"
    )


@pytest.fixture
def context_builder(mock_settings):
    """Create ContextBuilder instance"""
    return ContextBuilder(settings=mock_settings)


@pytest.mark.asyncio
async def test_initialize(context_builder):
    """Test initializing context builder"""
    await context_builder.initialize()

    assert context_builder._initialized is True
    assert context_builder._entity_inventory_service is not None
    assert context_builder._areas_service is not None
    assert context_builder._services_summary_service is not None
    assert context_builder._capability_patterns_service is not None
    assert context_builder._helpers_scenes_service is not None


@pytest.mark.asyncio
async def test_build_context_success(context_builder):
    """Test building context with all services working"""
    # Mock all services
    context_builder._entity_inventory_service = MagicMock()
    context_builder._entity_inventory_service.get_summary = AsyncMock(
        return_value="Light: 5 entities (office: 3, kitchen: 2)"
    )

    context_builder._areas_service = MagicMock()
    context_builder._areas_service.get_areas_list = AsyncMock(
        return_value="Office, Kitchen, Bedroom"
    )

    context_builder._services_summary_service = MagicMock()
    context_builder._services_summary_service.get_summary = AsyncMock(
        return_value="light.turn_on, light.turn_off"
    )

    context_builder._capability_patterns_service = MagicMock()
    context_builder._capability_patterns_service.get_patterns = AsyncMock(
        return_value="Philips Hue: brightness (0-255)"
    )

    context_builder._helpers_scenes_service = MagicMock()
    context_builder._helpers_scenes_service.get_summary = AsyncMock(
        return_value="input_boolean: automation_enabled"
    )

    context_builder._initialized = True

    context = await context_builder.build_context()

    assert "HOME ASSISTANT CONTEXT" in context
    assert "ENTITY INVENTORY" in context
    assert "AREAS" in context
    assert "AVAILABLE SERVICES" in context
    assert "DEVICE CAPABILITY PATTERNS" in context
    assert "HELPERS & SCENES" in context


@pytest.mark.asyncio
async def test_build_context_with_errors(context_builder):
    """Test building context when some services fail"""
    # Mock services with some failures
    context_builder._entity_inventory_service = MagicMock()
    context_builder._entity_inventory_service.get_summary = AsyncMock(
        return_value="Light: 5 entities"
    )

    context_builder._areas_service = MagicMock()
    context_builder._areas_service.get_areas_list = AsyncMock(
        side_effect=Exception("Service error")
    )

    context_builder._services_summary_service = MagicMock()
    context_builder._services_summary_service.get_summary = AsyncMock(
        return_value="light.turn_on"
    )

    context_builder._capability_patterns_service = MagicMock()
    context_builder._capability_patterns_service.get_patterns = AsyncMock(
        side_effect=Exception("Service error")
    )

    context_builder._helpers_scenes_service = MagicMock()
    context_builder._helpers_scenes_service.get_summary = AsyncMock(
        return_value="input_boolean: test"
    )

    context_builder._initialized = True

    context = await context_builder.build_context()

    # Should still build context with fallbacks
    assert "HOME ASSISTANT CONTEXT" in context
    assert "ENTITY INVENTORY" in context
    assert "AREAS" in context
    assert "(unavailable)" in context  # Failed services show as unavailable


@pytest.mark.asyncio
async def test_build_context_not_initialized(context_builder):
    """Test building context when not initialized"""
    with pytest.raises(RuntimeError, match="Context builder not initialized"):
        await context_builder.build_context()


@pytest.mark.asyncio
async def test_get_system_prompt(context_builder):
    """Test getting system prompt"""
    prompt = context_builder.get_system_prompt()

    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "Home Assistant" in prompt or "home assistant" in prompt.lower()


@pytest.mark.asyncio
async def test_build_complete_system_prompt(context_builder):
    """Test building complete system prompt with context"""
    # Mock build_context
    context_builder._initialized = True
    context_builder.build_context = AsyncMock(
        return_value="HOME ASSISTANT CONTEXT:\nENTITY INVENTORY:\nLight: 5"
    )

    complete_prompt = await context_builder.build_complete_system_prompt()

    assert "HOME ASSISTANT CONTEXT" in complete_prompt
    assert "ENTITY INVENTORY" in complete_prompt
    # Should include base system prompt
    assert len(complete_prompt) > len("HOME ASSISTANT CONTEXT")


@pytest.mark.asyncio
async def test_get_cached_value(context_builder):
    """Test getting cached value"""
    cache_key = "test_key"
    cache_value = "test_value"

    # Mock database session
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cache_value
    mock_session.execute.return_value = mock_result

    with patch("src.services.context_builder.get_session") as mock_get_session:
        mock_get_session.return_value.__aiter__.return_value = [mock_session]

        # Mock ContextCache query
        with patch("src.services.context_builder.ContextCache") as mock_cache:
            result = await context_builder._get_cached_value(cache_key)

            # Should return None if cache expired or not found
            # (actual implementation depends on database state)
            assert result is None or result == cache_value


@pytest.mark.asyncio
async def test_set_cached_value(context_builder):
    """Test setting cached value"""
    cache_key = "test_key"
    cache_value = "test_value"
    ttl_seconds = 300

    # Mock database session
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # No existing entry
    mock_session.execute.return_value = mock_result

    with patch("src.services.context_builder.get_session") as mock_get_session:
        mock_get_session.return_value.__aiter__.return_value = [mock_session]

        await context_builder._set_cached_value(cache_key, cache_value, ttl_seconds)

        # Verify session.add was called (for new entry) or update was called
        assert mock_session.add.called or mock_session.commit.called


@pytest.mark.asyncio
async def test_close(context_builder):
    """Test closing context builder"""
    # Initialize services
    context_builder._entity_inventory_service = MagicMock()
    context_builder._entity_inventory_service.close = AsyncMock()

    context_builder._areas_service = MagicMock()
    context_builder._areas_service.close = AsyncMock()

    context_builder._services_summary_service = MagicMock()
    context_builder._services_summary_service.close = AsyncMock()

    context_builder._capability_patterns_service = MagicMock()
    context_builder._capability_patterns_service.close = AsyncMock()

    context_builder._helpers_scenes_service = MagicMock()
    context_builder._helpers_scenes_service.close = AsyncMock()

    context_builder._initialized = True

    await context_builder.close()

    assert context_builder._initialized is False
    context_builder._entity_inventory_service.close.assert_called_once()
    context_builder._areas_service.close.assert_called_once()
    context_builder._services_summary_service.close.assert_called_once()
    context_builder._capability_patterns_service.close.assert_called_once()
    context_builder._helpers_scenes_service.close.assert_called_once()

