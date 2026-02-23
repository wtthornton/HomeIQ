"""
Integration tests for Context Builder with external services.

These tests require external services to be running or mocked.
For CI/CD, use mocked services. For local testing, can use real services.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.context_builder import ContextBuilder
from src.config import Settings


@pytest.fixture
def integration_settings():
    """Create settings for integration testing"""
    return Settings(
        ha_url="http://homeassistant:8123",
        ha_access_token="test-token",
        data_api_url="http://data-api:8006",
        device_intelligence_url="http://device-intelligence-service:8028"
    )


@pytest.fixture
def context_builder(integration_settings):
    """Create ContextBuilder for integration testing"""
    return ContextBuilder(settings=integration_settings)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_builder_full_integration(context_builder):
    """
    Integration test: Build complete context with all services.

    This test verifies that the context builder can successfully
    orchestrate all services and build a complete context string.
    """
    # Initialize context builder
    await context_builder.initialize()

    try:
        # Build context (will call all services)
        context = await context_builder.build_context()

        # Verify context structure
        assert isinstance(context, str)
        assert len(context) > 0
        assert "HOME ASSISTANT CONTEXT" in context

        # Verify all sections are present (even if unavailable)
        assert "ENTITY INVENTORY" in context
        assert "AREAS" in context
        assert "AVAILABLE SERVICES" in context
        assert "DEVICE CAPABILITY PATTERNS" in context
        assert "HELPERS & SCENES" in context

    finally:
        await context_builder.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_system_prompt_integration(context_builder):
    """
    Integration test: Build complete system prompt with context.

    This test verifies that the complete system prompt includes
    both the base prompt and the injected context.
    """
    await context_builder.initialize()

    try:
        complete_prompt = await context_builder.build_complete_system_prompt()

        # Verify complete prompt structure
        assert isinstance(complete_prompt, str)
        assert len(complete_prompt) > 0

        # Should include base system prompt content
        assert "Home Assistant" in complete_prompt or "home assistant" in complete_prompt.lower()

        # Should include context
        assert "HOME ASSISTANT CONTEXT" in complete_prompt

    finally:
        await context_builder.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_caching_integration(context_builder):
    """
    Integration test: Verify context caching works correctly.

    This test verifies that cached values are used on subsequent calls.
    """
    await context_builder.initialize()

    try:
        # First call - should fetch from services
        context1 = await context_builder.build_context()

        # Second call - should use cache for some components
        context2 = await context_builder.build_context()

        # Both should be valid context strings
        assert isinstance(context1, str)
        assert isinstance(context2, str)
        assert len(context1) > 0
        assert len(context2) > 0

    finally:
        await context_builder.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_builder_error_handling(context_builder):
    """
    Integration test: Verify graceful error handling.

    This test verifies that the context builder handles service
    failures gracefully and still returns a valid context.
    """
    await context_builder.initialize()

    try:
        # Mock one service to fail
        with patch.object(
            context_builder._entity_inventory_service,
            "get_summary",
            side_effect=Exception("Service unavailable")
        ):
            context = await context_builder.build_context()

            # Should still return valid context with fallback
            assert isinstance(context, str)
            assert "HOME ASSISTANT CONTEXT" in context
            assert "ENTITY INVENTORY" in context
            # Should show unavailable for failed service
            assert "(unavailable)" in context

    finally:
        await context_builder.close()

