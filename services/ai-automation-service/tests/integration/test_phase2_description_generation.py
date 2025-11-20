"""
Integration Tests for Phase 2 - Description-Only Generation
============================================================

Story AI1.23 Phase 2: Conversational Suggestion Refinement

Tests the complete flow:
1. Pattern → DescriptionGenerator → OpenAI → Description
2. Device capabilities fetching from data-api
3. End-to-end /generate endpoint

These tests require:
- OpenAI API key set
- data-api running on localhost:8006
- Database initialized
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytest.importorskip(
    "transformers",
    reason="transformers dependency not available in this environment"
)

from src.clients.data_api_client import DataAPIClient
from src.llm.description_generator import DescriptionGenerator
from src.main import app

# ============================================================================
# Integration Tests (Real OpenAI calls - use with caution!)
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv('OPENAI_API_KEY'),
    reason="OPENAI_API_KEY not set - skipping real API tests"
)
@pytest.mark.asyncio
async def test_real_openai_description_generation():
    """
    Test real OpenAI description generation (COSTS MONEY - ~$0.00006).
    
    This is a real integration test that calls OpenAI API.
    Only run when you want to verify the actual integration works.
    """
    from openai import AsyncOpenAI

    # Initialize real OpenAI client
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    generator = DescriptionGenerator(client, model="gpt-4o-mini")

    # Test pattern
    pattern = {
        'pattern_type': 'time_of_day',
        'device_id': 'light.kitchen',
        'hour': 7,
        'minute': 0,
        'occurrences': 28,
        'confidence': 0.92
    }

    device_context = {
        'name': 'Kitchen Light',
        'area': 'Kitchen',
        'domain': 'light'
    }

    # Generate description (REAL OpenAI call!)
    description = await generator.generate_description(pattern, device_context)

    # Assertions
    assert description is not None
    assert len(description) > 0
    assert "kitchen" in description.lower() or "7" in description or "morning" in description.lower()
    assert "alias:" not in description  # No YAML!
    assert "trigger:" not in description

    # Check token usage was tracked
    stats = generator.get_usage_stats()
    assert stats['total_tokens'] > 0
    assert stats['estimated_cost_usd'] > 0

    print("\n✅ Real OpenAI test passed!")
    print(f"   Description: {description}")
    print(f"   Tokens: {stats['total_tokens']}")
    print(f"   Cost: ${stats['estimated_cost_usd']:.6f}")


# ============================================================================
# Mocked Integration Tests (No cost)
# ============================================================================

@pytest.mark.asyncio
async def test_generate_endpoint_with_mocked_openai():
    """Test /generate endpoint with mocked OpenAI"""

    with patch('src.api.conversational_router.description_generator') as mock_gen:
        # Mock OpenAI response
        mock_gen.generate_description = AsyncMock(
            return_value="At 7:00 AM every morning, turn on the Kitchen Light to help you wake up"
        )

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/suggestions/generate",
                json={
                    "pattern_id": 123,
                    "pattern_type": "time_of_day",
                    "device_id": "light.kitchen",
                    "metadata": {
                        "avg_time_decimal": 7.0,
                        "confidence": 0.92
                    }
                }
            )

            assert response.status_code == 201
            data = response.json()

            assert data['description'] == "At 7:00 AM every morning, turn on the Kitchen Light to help you wake up"
            assert data['status'] == 'draft'
            assert 'devices_involved' in data


@pytest.mark.asyncio
async def test_capabilities_endpoint_with_mocked_data_api():
    """Test /devices/{id}/capabilities endpoint with mocked data-api"""

    with patch('src.api.conversational_router.data_api_client') as mock_client:
        # Mock capabilities response
        mock_client.fetch_device_capabilities = AsyncMock(
            return_value={
                "entity_id": "light.living_room",
                "friendly_name": "Living Room Light",
                "domain": "light",
                "area": "Living Room",
                "supported_features": {
                    "brightness": True,
                    "rgb_color": True,
                    "color_temp": True
                },
                "friendly_capabilities": [
                    "Adjust brightness (0-100%)",
                    "Change color (RGB)",
                    "Set color temperature (warm to cool)"
                ]
            }
        )

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/suggestions/devices/light.living_room/capabilities"
            )

            assert response.status_code == 200
            data = response.json()

            assert data['entity_id'] == 'light.living_room'
            assert data['friendly_name'] == 'Living Room Light'
            assert 'brightness' in data['supported_features']
            assert len(data['friendly_capabilities']) == 3


# ============================================================================
# End-to-End Flow Tests
# ============================================================================

@pytest.mark.asyncio
async def test_complete_phase2_flow():
    """
    Test complete Phase 2 flow with mocked dependencies.
    
    Flow:
    1. Call /generate endpoint
    2. Description is generated (mocked)
    3. Capabilities are fetched (mocked)
    4. Suggestion is created in database
    5. Response includes description and capabilities
    """

    with patch('src.api.conversational_router.description_generator') as mock_gen, \
         patch('src.api.conversational_router.data_api_client') as mock_data_api:

        # Mock OpenAI description
        mock_gen.generate_description = AsyncMock(
            return_value="When motion is detected in the Living Room after 6PM, turn on the Living Room Light"
        )

        # Mock capabilities
        mock_data_api.fetch_device_capabilities = AsyncMock(
            return_value={
                "entity_id": "light.living_room",
                "friendly_name": "Living Room Light",
                "domain": "light",
                "area": "Living Room",
                "supported_features": {"brightness": True, "rgb_color": True},
                "friendly_capabilities": ["Adjust brightness", "Change color"]
            }
        )

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Generate description
            response = await client.post(
                "/api/v1/suggestions/generate",
                json={
                    "pattern_id": 456,
                    "pattern_type": "time_of_day",
                    "device_id": "light.living_room",
                    "metadata": {"avg_time_decimal": 18.0}
                }
            )

            assert response.status_code == 201
            suggestion_data = response.json()

            # Verify description
            assert "Living Room" in suggestion_data['description']
            assert "alias:" not in suggestion_data['description']  # No YAML!

            # Verify status
            assert suggestion_data['status'] == 'draft'

            # Verify capabilities are included
            assert len(suggestion_data['devices_involved']) > 0
            device = suggestion_data['devices_involved'][0]
            assert device['entity_id'] == 'light.living_room'
            assert 'brightness' in device['capabilities']['supported_features']
            assert 'rgb_color' in device['capabilities']['supported_features']


@pytest.mark.asyncio
async def test_phase2_error_handling():
    """Test error handling when OpenAI or data-api fails"""

    with patch('src.api.conversational_router.description_generator') as mock_gen:
        # Mock OpenAI failure
        mock_gen.generate_description = AsyncMock(
            side_effect=Exception("OpenAI API timeout")
        )

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/suggestions/generate",
                json={
                    "pattern_id": 789,
                    "pattern_type": "time_of_day",
                    "device_id": "light.kitchen",
                    "metadata": {}
                }
            )

            # Should return 500 error
            assert response.status_code == 500
            assert "Failed to generate description" in response.json()['detail']


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.asyncio
async def test_description_generation_performance():
    """Test that description generation completes within reasonable time"""
    import time

    with patch('src.api.conversational_router.description_generator') as mock_gen, \
         patch('src.api.conversational_router.data_api_client') as mock_data_api:

        # Mock fast responses
        mock_gen.generate_description = AsyncMock(return_value="Test description")
        mock_data_api.fetch_device_capabilities = AsyncMock(return_value={
            "entity_id": "light.test",
            "friendly_name": "Test Light",
            "domain": "light",
            "supported_features": {},
            "friendly_capabilities": []
        })

        async with AsyncClient(app=app, base_url="http://test") as client:
            start = time.time()

            response = await client.post(
                "/api/v1/suggestions/generate",
                json={
                    "pattern_id": 999,
                    "pattern_type": "time_of_day",
                    "device_id": "light.test",
                    "metadata": {}
                }
            )

            elapsed = time.time() - start

            assert response.status_code == 201
            assert elapsed < 5.0  # Should complete within 5 seconds


# ============================================================================
# Capability Parsing Tests
# ============================================================================

@pytest.mark.asyncio
async def test_light_capability_parsing():
    """Test that light capabilities are parsed correctly"""

    mock_entity_data = {
        "entity_id": "light.bedroom",
        "friendly_name": "Bedroom Light",
        "area_id": "Bedroom",
        "attributes": {
            "brightness": 128,
            "rgb_color": [255, 0, 0],
            "color_temp": 400,
            "supported_color_modes": ["rgb", "color_temp"]
        }
    }

    client = DataAPIClient(base_url="http://test")
    capabilities = client._parse_capabilities("light.bedroom", mock_entity_data)

    # Assert all light features detected
    assert capabilities['supported_features']['brightness'] == True
    assert capabilities['supported_features']['rgb_color'] == True
    assert capabilities['supported_features']['color_temp'] == True
    assert capabilities['supported_features']['transition'] == True

    # Assert friendly capabilities
    assert len(capabilities['friendly_capabilities']) >= 3
    assert any('brightness' in cap.lower() for cap in capabilities['friendly_capabilities'])
    assert any('color' in cap.lower() for cap in capabilities['friendly_capabilities'])


@pytest.mark.asyncio
async def test_climate_capability_parsing():
    """Test that climate/thermostat capabilities are parsed correctly"""

    mock_entity_data = {
        "entity_id": "climate.living_room",
        "friendly_name": "Living Room Thermostat",
        "area_id": "Living Room",
        "attributes": {
            "temperature": 72,
            "min_temp": 60,
            "max_temp": 90,
            "hvac_modes": ["off", "heat", "cool", "auto"],
            "fan_modes": ["auto", "low", "high"],
            "preset_modes": ["home", "away", "sleep"]
        }
    }

    client = DataAPIClient(base_url="http://test")
    capabilities = client._parse_capabilities("climate.living_room", mock_entity_data)

    # Assert climate features detected
    assert capabilities['supported_features']['temperature'] == True
    assert capabilities['supported_features']['hvac_mode'] == True
    assert capabilities['supported_features']['fan_mode'] == True
    assert capabilities['supported_features']['preset'] == True

    # Assert temperature range in description
    assert any('60°-90°' in cap for cap in capabilities['friendly_capabilities'])


# ============================================================================
# Pytest Configuration
# ============================================================================

@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio for async tests"""
    return "asyncio"

