"""Tests for Services Summary Service"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.services_summary_service import ServicesSummaryService
from src.config import Settings
from src.services.context_builder import ContextBuilder


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    return Settings(
        ha_url="http://test-ha:8123",
        ha_token="test-token"
    )


@pytest.fixture
def mock_context_builder():
    """Create mock context builder"""
    builder = MagicMock(spec=ContextBuilder)
    builder._get_cached_value = AsyncMock(return_value=None)
    builder._set_cached_value = AsyncMock()
    return builder


@pytest.fixture
def services_summary_service(mock_settings, mock_context_builder):
    """Create ServicesSummaryService instance"""
    return ServicesSummaryService(
        settings=mock_settings,
        context_builder=mock_context_builder
    )


@pytest.mark.asyncio
async def test_get_summary_with_services(services_summary_service, mock_context_builder):
    """Test getting summary with services"""
    mock_services = {
        "light": {
            "turn_on": {"fields": {}},
            "turn_off": {"fields": {}},
            "set_brightness": {"fields": {"brightness_pct": {}}}
        },
        "switch": {
            "turn_on": {"fields": {}},
            "turn_off": {"fields": {}}
        }
    }

    with patch.object(
        services_summary_service.ha_client,
        "get_services",
        new_callable=AsyncMock,
        return_value=mock_services
    ):
        summary = await services_summary_service.get_summary()

        assert "light" in summary
        assert "switch" in summary
        assert "turn_on" in summary
        assert "set_brightness" in summary
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_summary_empty(services_summary_service, mock_context_builder):
    """Test getting summary with no services"""
    with patch.object(
        services_summary_service.ha_client,
        "get_services",
        new_callable=AsyncMock,
        return_value={}
    ):
        summary = await services_summary_service.get_summary()

        assert "No services available" in summary
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_format_parameter_hint(services_summary_service):
    """Test parameter hint formatting"""
    # Test brightness hint
    hint = services_summary_service._format_parameter_hint(
        "set_brightness",
        {"brightness_pct": {}}
    )
    assert "brightness_pct: 0-100" in hint

    # Test rgb_color hint
    hint = services_summary_service._format_parameter_hint(
        "set_color",
        {"rgb_color": {}}
    )
    assert "rgb_color" in hint


@pytest.mark.asyncio
async def test_close(services_summary_service):
    """Test closing service resources"""
    services_summary_service.ha_client.close = AsyncMock()

    await services_summary_service.close()

    services_summary_service.ha_client.close.assert_called_once()

