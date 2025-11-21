"""
Unit tests for DescriptionGenerator - Story AI1.23 Phase 2
===========================================================

Tests description-only generation without YAML.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.llm.description_generator import SYSTEM_PROMPT_DESCRIPTION, DescriptionGenerator


@pytest.fixture
def mock_openai_client():
    """Mock AsyncOpenAI client"""
    return AsyncMock()


@pytest.fixture
def description_generator(mock_openai_client):
    """Create DescriptionGenerator with mocked client"""
    return DescriptionGenerator(mock_openai_client, model="gpt-4o-mini")


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "When motion is detected in the Living Room after 6PM, turn on the Living Room Light to 50% brightness"
    response.usage = MagicMock()
    response.usage.prompt_tokens = 150
    response.usage.completion_tokens = 25
    response.usage.total_tokens = 175
    return response


# ============================================================================
# Basic Functionality Tests
# ============================================================================

@pytest.mark.asyncio
async def test_generate_description_time_of_day(description_generator, mock_openai_client, mock_openai_response):
    """Test description generation for time-of-day pattern"""
    # Setup
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

    pattern = {
        "pattern_type": "time_of_day",
        "device_id": "light.living_room",
        "hour": 18,
        "minute": 0,
        "occurrences": 24,
        "confidence": 0.89,
    }

    device_context = {
        "name": "Living Room Light",
        "area": "Living Room",
        "domain": "light",
    }

    # Execute
    description = await description_generator.generate_description(pattern, device_context)

    # Assert
    assert description == "When motion is detected in the Living Room after 6PM, turn on the Living Room Light to 50% brightness"
    assert "Living Room" in description
    assert "light.living_room" not in description  # No entity IDs!
    assert "alias:" not in description  # No YAML!

    # Verify OpenAI was called correctly
    mock_openai_client.chat.completions.create.assert_called_once()
    call_args = mock_openai_client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == "gpt-4o-mini"
    assert call_args.kwargs["temperature"] == 0.7
    assert call_args.kwargs["max_tokens"] == 200
    assert call_args.kwargs["messages"][0]["role"] == "system"
    assert call_args.kwargs["messages"][0]["content"] == SYSTEM_PROMPT_DESCRIPTION


@pytest.mark.asyncio
async def test_generate_description_co_occurrence(description_generator, mock_openai_client):
    """Test description generation for co-occurrence pattern"""
    # Setup
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "When you turn on the Living Room Light, automatically turn on the Living Room Fan"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 160
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 180

    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    pattern = {
        "pattern_type": "co_occurrence",
        "device1": "light.living_room",
        "device2": "fan.living_room",
        "occurrences": 22,
        "confidence": 0.85,
        "metadata": {"avg_time_delta_seconds": 45},
    }

    device_context = {
        "device1": {"name": "Living Room Light"},
        "device2": {"name": "Living Room Fan"},
    }

    # Execute
    description = await description_generator.generate_description(pattern, device_context)

    # Assert
    assert "Living Room Light" in description
    assert "Living Room Fan" in description
    assert "light.living_room" not in description
    assert "fan.living_room" not in description


@pytest.mark.asyncio
async def test_generate_description_anomaly(description_generator, mock_openai_client):
    """Test description generation for anomaly pattern"""
    # Setup
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Get notified when the Garage Door is activated at unexpected times"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 140
    mock_response.usage.completion_tokens = 15
    mock_response.usage.total_tokens = 155

    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    pattern = {
        "pattern_type": "anomaly",
        "device_id": "cover.garage_door",
        "confidence": 0.78,
        "metadata": {"anomaly_score": 0.92},
    }

    device_context = {
        "name": "Garage Door",
    }

    # Execute
    description = await description_generator.generate_description(pattern, device_context)

    # Assert
    assert "Garage Door" in description
    assert "cover.garage_door" not in description


# ============================================================================
# YAML Filtering Tests
# ============================================================================

@pytest.mark.asyncio
async def test_filters_yaml_from_response(description_generator, mock_openai_client):
    """Test that YAML is filtered out if OpenAI returns it despite instructions"""
    # Setup - OpenAI returns YAML despite instructions
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """When motion detected, turn on light

alias: "Motion Light"
trigger:
  - platform: state"""
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 150
    mock_response.usage.completion_tokens = 30
    mock_response.usage.total_tokens = 180

    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    pattern = {
        "pattern_type": "time_of_day",
        "device_id": "light.kitchen",
        "hour": 7,
        "minute": 0,
    }

    # Execute
    description = await description_generator.generate_description(pattern, None)

    # Assert - YAML should be filtered out
    assert description == "When motion detected, turn on light"
    assert "alias:" not in description
    assert "trigger:" not in description


# ============================================================================
# Token Usage Tests
# ============================================================================

@pytest.mark.asyncio
async def test_tracks_token_usage(description_generator, mock_openai_client, mock_openai_response):
    """Test that token usage is tracked correctly"""
    # Setup
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

    pattern = {
        "pattern_type": "time_of_day",
        "device_id": "light.kitchen",
        "hour": 7,
        "minute": 0,
    }

    # Execute
    await description_generator.generate_description(pattern, None)

    # Assert
    stats = description_generator.get_usage_stats()
    assert stats["total_tokens"] == 175
    assert stats["input_tokens"] == 150
    assert stats["output_tokens"] == 25
    assert stats["estimated_cost_usd"] > 0
    assert stats["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_resets_token_usage(description_generator, mock_openai_client, mock_openai_response):
    """Test that token usage can be reset"""
    # Setup
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

    pattern = {
        "pattern_type": "time_of_day",
        "device_id": "light.kitchen",
        "hour": 7,
    }

    # Generate description to accumulate tokens
    await description_generator.generate_description(pattern, None)
    assert description_generator.get_usage_stats()["total_tokens"] == 175

    # Reset
    description_generator.reset_usage_stats()

    # Assert reset
    stats = description_generator.get_usage_stats()
    assert stats["total_tokens"] == 0
    assert stats["input_tokens"] == 0
    assert stats["output_tokens"] == 0


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_retries_on_failure(description_generator, mock_openai_client, mock_openai_response):
    """Test that API calls are retried on failure"""
    # Setup - fail twice, succeed on third attempt
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=[
            Exception("API timeout"),
            Exception("Rate limit"),
            mock_openai_response,
        ],
    )

    pattern = {
        "pattern_type": "time_of_day",
        "device_id": "light.kitchen",
        "hour": 7,
    }

    # Execute - should succeed after retries
    description = await description_generator.generate_description(pattern, None)

    # Assert
    assert description is not None
    assert mock_openai_client.chat.completions.create.call_count == 3


@pytest.mark.asyncio
async def test_raises_after_max_retries(description_generator, mock_openai_client):
    """Test that exception is raised after max retries"""
    # Setup - always fail
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=Exception("API error"),
    )

    pattern = {
        "pattern_type": "time_of_day",
        "device_id": "light.kitchen",
        "hour": 7,
    }

    # Execute - should raise after 3 retries
    with pytest.raises(Exception, match="API error"):
        await description_generator.generate_description(pattern, None)

    # Assert - tried 3 times
    assert mock_openai_client.chat.completions.create.call_count == 3


# ============================================================================
# Prompt Building Tests
# ============================================================================

def test_build_time_of_day_prompt(description_generator):
    """Test time-of-day prompt includes correct information"""
    pattern = {
        "pattern_type": "time_of_day",
        "device_id": "light.kitchen",
        "hour": 18,
        "minute": 30,
        "occurrences": 24,
        "confidence": 0.89,
    }

    device_context = {
        "name": "Kitchen Light",
        "area": "Kitchen",
        "domain": "light",
    }

    prompt = description_generator._build_time_of_day_prompt(pattern, device_context)

    # Assert prompt includes key information
    assert "Kitchen Light" in prompt
    assert "Kitchen" in prompt
    assert "18:30" in prompt
    assert "24" in prompt  # occurrences
    assert "89%" in prompt  # confidence
    assert "light.kitchen" in prompt  # entity ID for reference


def test_build_co_occurrence_prompt(description_generator):
    """Test co-occurrence prompt includes both devices"""
    pattern = {
        "pattern_type": "co_occurrence",
        "device1": "light.living_room",
        "device2": "fan.living_room",
        "occurrences": 22,
        "confidence": 0.85,
        "metadata": {"avg_time_delta_seconds": 45},
    }

    device_context = {
        "device1": {"name": "Living Room Light"},
        "device2": {"name": "Living Room Fan"},
    }

    prompt = description_generator._build_co_occurrence_prompt(pattern, device_context)

    # Assert prompt includes both devices
    assert "Living Room Light" in prompt
    assert "Living Room Fan" in prompt
    assert "45 seconds" in prompt or "45" in prompt
    assert "22" in prompt  # occurrences


# ============================================================================
# Integration Tests (with real patterns)
# ============================================================================

@pytest.mark.asyncio
async def test_generate_from_real_pattern_structure(description_generator, mock_openai_client, mock_openai_response):
    """Test with pattern structure matching actual database records"""
    # Setup
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

    # Real pattern structure from database
    pattern = {
        "id": 123,
        "pattern_type": "time_of_day",
        "device_id": "light.kitchen_ceiling",
        "confidence": 0.92,
        "occurrences": 28,
        "metadata": {
            "hour": 7,
            "minute": 0,
            "avg_time_decimal": 7.0,
        },
    }

    # Execute
    description = await description_generator.generate_description(pattern, None)

    # Assert
    assert description is not None
    assert len(description) > 0
    assert "alias:" not in description


@pytest.mark.asyncio
async def test_handles_missing_device_context(description_generator, mock_openai_client, mock_openai_response):
    """Test that generator works without device context"""
    # Setup
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

    pattern = {
        "pattern_type": "time_of_day",
        "device_id": "light.unknown_device",
        "hour": 12,
        "minute": 0,
    }

    # Execute - no device_context provided
    description = await description_generator.generate_description(pattern, None)

    # Assert - should use entity_id as fallback
    assert description is not None
    # May contain either friendly name or entity ID

