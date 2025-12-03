"""Tests for Capability Patterns Service"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.capability_patterns_service import CapabilityPatternsService
from src.config import Settings
from src.services.context_builder import ContextBuilder


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    return Settings(
        device_intelligence_url="http://test-device-intel:8028"
    )


@pytest.fixture
def mock_context_builder():
    """Create mock context builder"""
    builder = MagicMock(spec=ContextBuilder)
    builder._get_cached_value = AsyncMock(return_value=None)
    builder._set_cached_value = AsyncMock()
    return builder


@pytest.fixture
def capability_patterns_service(mock_settings, mock_context_builder):
    """Create CapabilityPatternsService instance"""
    return CapabilityPatternsService(
        settings=mock_settings,
        context_builder=mock_context_builder
    )


@pytest.mark.asyncio
async def test_get_patterns_with_capabilities(capability_patterns_service, mock_context_builder):
    """Test getting patterns with device capabilities"""
    # Mock devices response
    mock_devices = [
        {"device_id": "device1", "manufacturer": "Philips", "model": "Hue"},
        {"device_id": "device2", "manufacturer": "WLED", "model": "Strip"},
    ]

    # Mock capabilities response
    mock_capabilities_device1 = [
        {
            "capability_name": "brightness",
            "capability_type": "numeric",
            "properties": {"min": 0, "max": 255}
        },
        {
            "capability_name": "color_mode",
            "capability_type": "enum",
            "properties": {"values": ["rgb", "hs", "xy"]}
        }
    ]

    mock_capabilities_device2 = [
        {
            "capability_name": "effect",
            "capability_type": "enum",
            "properties": {"count": 186}
        }
    ]

    with patch.object(
        capability_patterns_service.device_intelligence_client,
        "get_devices",
        new_callable=AsyncMock,
        return_value=mock_devices
    ), patch.object(
        capability_patterns_service.device_intelligence_client,
        "get_device_capabilities",
        new_callable=AsyncMock,
        side_effect=[mock_capabilities_device1, mock_capabilities_device2]
    ):
        patterns = await capability_patterns_service.get_patterns()

        # Verify patterns contain expected content
        assert "brightness" in patterns or "Brightness" in patterns
        assert "effect" in patterns or "Effect" in patterns

        # Verify cache was set
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_patterns_empty_devices(capability_patterns_service, mock_context_builder):
    """Test getting patterns with no devices"""
    with patch.object(
        capability_patterns_service.device_intelligence_client,
        "get_devices",
        new_callable=AsyncMock,
        return_value=[]
    ):
        patterns = await capability_patterns_service.get_patterns()

        assert "No device capability patterns available" in patterns
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_patterns_cached(capability_patterns_service, mock_context_builder):
    """Test getting patterns from cache"""
    cached_patterns = "Cached patterns: Philips Hue: brightness (0-255), color_mode (3 options)"
    mock_context_builder._get_cached_value = AsyncMock(return_value=cached_patterns)

    patterns = await capability_patterns_service.get_patterns()

    assert patterns == cached_patterns
    # Should not call get_devices when cached
    assert not hasattr(capability_patterns_service.device_intelligence_client, "get_devices") or \
           not capability_patterns_service.device_intelligence_client.get_devices.called


@pytest.mark.asyncio
async def test_get_patterns_api_error(capability_patterns_service, mock_context_builder):
    """Test handling API errors gracefully"""
    with patch.object(
        capability_patterns_service.device_intelligence_client,
        "get_devices",
        new_callable=AsyncMock,
        side_effect=Exception("API Error")
    ):
        patterns = await capability_patterns_service.get_patterns()

        assert "unavailable" in patterns.lower()
        # Should not cache errors
        mock_context_builder._set_cached_value.assert_not_called()


@pytest.mark.asyncio
async def test_get_patterns_device_capability_error(capability_patterns_service, mock_context_builder):
    """Test handling errors when fetching individual device capabilities"""
    mock_devices = [
        {"device_id": "device1", "manufacturer": "Philips", "model": "Hue"},
    ]

    with patch.object(
        capability_patterns_service.device_intelligence_client,
        "get_devices",
        new_callable=AsyncMock,
        return_value=mock_devices
    ), patch.object(
        capability_patterns_service.device_intelligence_client,
        "get_device_capabilities",
        new_callable=AsyncMock,
        side_effect=Exception("Capability fetch error")
    ):
        patterns = await capability_patterns_service.get_patterns()

        # Should still return a result (possibly empty or fallback)
        assert isinstance(patterns, str)
        # Should not raise exception


@pytest.mark.asyncio
async def test_format_capability_numeric(capability_patterns_service):
    """Test formatting numeric capability"""
    formatted = capability_patterns_service._format_capability(
        "brightness", "numeric", {"min": 0, "max": 255}
    )
    assert "brightness" in formatted
    assert "0-255" in formatted or "255" in formatted


@pytest.mark.asyncio
async def test_format_capability_enum(capability_patterns_service):
    """Test formatting enum capability"""
    formatted = capability_patterns_service._format_capability(
        "color_mode", "enum", {"values": ["rgb", "hs"]}
    )
    assert "color_mode" in formatted
    assert "2" in formatted or "options" in formatted


@pytest.mark.asyncio
async def test_close(capability_patterns_service):
    """Test closing service resources"""
    capability_patterns_service.device_intelligence_client.close = AsyncMock()

    await capability_patterns_service.close()

    capability_patterns_service.device_intelligence_client.close.assert_called_once()

