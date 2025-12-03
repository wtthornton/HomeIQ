"""
Performance tests for HA AI Agent Service.

Tests verify that performance requirements are met:
- Context building < 100ms with cache
- Context building < 500ms without cache (first call)
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.context_builder import ContextBuilder
from src.config import Settings


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
async def test_context_build_performance_with_cache(context_builder):
    """
    Performance test: Context building with cache should be < 100ms.

    This test verifies that cached context building meets the
    performance requirement of < 100ms.
    """
    # Setup services with cached responses
    context_builder._entity_inventory_service = MagicMock()
    context_builder._entity_inventory_service.get_summary = AsyncMock(
        return_value="Light: 5 entities"
    )

    context_builder._areas_service = MagicMock()
    context_builder._areas_service.get_areas_list = AsyncMock(
        return_value="Office, Kitchen"
    )

    context_builder._services_summary_service = MagicMock()
    context_builder._services_summary_service.get_summary = AsyncMock(
        return_value="light.turn_on"
    )

    context_builder._capability_patterns_service = MagicMock()
    context_builder._capability_patterns_service.get_patterns = AsyncMock(
        return_value="Philips Hue: brightness"
    )

    context_builder._helpers_scenes_service = MagicMock()
    context_builder._helpers_scenes_service.get_summary = AsyncMock(
        return_value="input_boolean: test"
    )

    context_builder._initialized = True

    # Mock cache to return cached values (simulating cache hit)
    async def mock_get_cached(key):
        if key in ["entity_inventory", "areas", "services", "capability_patterns", "helpers_scenes"]:
            return "cached_value"
        return None

    context_builder._get_cached_value = AsyncMock(side_effect=mock_get_cached)

    # Measure performance
    start_time = time.perf_counter()
    context = await context_builder.build_context()
    elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

    # Verify performance requirement
    assert elapsed_time < 100, f"Context building took {elapsed_time:.2f}ms, expected < 100ms"
    assert isinstance(context, str)
    assert len(context) > 0


@pytest.mark.asyncio
async def test_context_build_performance_first_call(context_builder):
    """
    Performance test: First call (without cache) should be < 500ms.

    This test verifies that the first context build (which requires
    API calls) meets the performance requirement of < 500ms.
    """
    # Setup services with fast mock responses
    context_builder._entity_inventory_service = MagicMock()
    context_builder._entity_inventory_service.get_summary = AsyncMock(
        return_value="Light: 5 entities"
    )

    context_builder._areas_service = MagicMock()
    context_builder._areas_service.get_areas_list = AsyncMock(
        return_value="Office, Kitchen"
    )

    context_builder._services_summary_service = MagicMock()
    context_builder._services_summary_service.get_summary = AsyncMock(
        return_value="light.turn_on"
    )

    context_builder._capability_patterns_service = MagicMock()
    context_builder._capability_patterns_service.get_patterns = AsyncMock(
        return_value="Philips Hue: brightness"
    )

    context_builder._helpers_scenes_service = MagicMock()
    context_builder._helpers_scenes_service.get_summary = AsyncMock(
        return_value="input_boolean: test"
    )

    context_builder._initialized = True

    # Mock cache to return None (simulating cache miss)
    context_builder._get_cached_value = AsyncMock(return_value=None)
    context_builder._set_cached_value = AsyncMock()

    # Measure performance
    start_time = time.perf_counter()
    context = await context_builder.build_context()
    elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

    # Verify performance requirement (first call can be slower)
    assert elapsed_time < 500, f"First context build took {elapsed_time:.2f}ms, expected < 500ms"
    assert isinstance(context, str)
    assert len(context) > 0


@pytest.mark.asyncio
async def test_system_prompt_performance(context_builder):
    """
    Performance test: System prompt retrieval should be fast.

    System prompt retrieval should be very fast (< 10ms) since
    it's just returning a constant string.
    """
    context_builder._initialized = True

    # Measure performance
    start_time = time.perf_counter()
    prompt = context_builder.get_system_prompt()
    elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

    # Verify performance (should be very fast)
    assert elapsed_time < 10, f"System prompt retrieval took {elapsed_time:.2f}ms, expected < 10ms"
    assert isinstance(prompt, str)
    assert len(prompt) > 0


@pytest.mark.asyncio
async def test_complete_prompt_performance(context_builder):
    """
    Performance test: Complete prompt building should meet requirements.

    Complete prompt building includes context, so should meet
    the same performance requirements as context building.
    """
    # Setup services
    context_builder._entity_inventory_service = MagicMock()
    context_builder._entity_inventory_service.get_summary = AsyncMock(
        return_value="Light: 5 entities"
    )

    context_builder._areas_service = MagicMock()
    context_builder._areas_service.get_areas_list = AsyncMock(
        return_value="Office, Kitchen"
    )

    context_builder._services_summary_service = MagicMock()
    context_builder._services_summary_service.get_summary = AsyncMock(
        return_value="light.turn_on"
    )

    context_builder._capability_patterns_service = MagicMock()
    context_builder._capability_patterns_service.get_patterns = AsyncMock(
        return_value="Philips Hue: brightness"
    )

    context_builder._helpers_scenes_service = MagicMock()
    context_builder._helpers_scenes_service.get_summary = AsyncMock(
        return_value="input_boolean: test"
    )

    context_builder._initialized = True

    # Mock cache
    context_builder._get_cached_value = AsyncMock(return_value="cached_value")

    # Measure performance
    start_time = time.perf_counter()
    complete_prompt = await context_builder.build_complete_system_prompt()
    elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

    # Verify performance requirement
    assert elapsed_time < 100, f"Complete prompt build took {elapsed_time:.2f}ms, expected < 100ms"
    assert isinstance(complete_prompt, str)
    assert len(complete_prompt) > 0
    assert "HOME ASSISTANT CONTEXT" in complete_prompt

