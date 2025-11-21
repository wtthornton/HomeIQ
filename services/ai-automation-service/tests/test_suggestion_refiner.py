"""
Unit tests for SuggestionRefiner - Story AI1.23 Phase 3
========================================================

Tests conversational refinement with natural language edits.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.llm.suggestion_refiner import SuggestionRefiner


@pytest.fixture
def mock_openai_client():
    """Mock AsyncOpenAI client"""
    return AsyncMock()


@pytest.fixture
def suggestion_refiner(mock_openai_client):
    """Create SuggestionRefiner with mocked client"""
    return SuggestionRefiner(mock_openai_client, model="gpt-4o-mini")


@pytest.fixture
def device_capabilities_rgb():
    """Device capabilities for RGB-capable light"""
    return {
        "entity_id": "light.living_room",
        "friendly_name": "Living Room Light",
        "domain": "light",
        "area": "Living Room",
        "supported_features": {
            "brightness": True,
            "rgb_color": True,
            "color_temp": True,
            "transition": True,
        },
        "friendly_capabilities": [
            "Adjust brightness (0-100%)",
            "Change color (RGB)",
            "Set color temperature (warm to cool)",
            "Smooth transitions (fade in/out)",
        ],
    }


@pytest.fixture
def device_capabilities_no_rgb():
    """Device capabilities for non-RGB light"""
    return {
        "entity_id": "light.bedroom",
        "friendly_name": "Bedroom Light",
        "domain": "light",
        "supported_features": {
            "brightness": True,
        },
        "friendly_capabilities": [
            "Adjust brightness (0-100%)",
        ],
    }


# ============================================================================
# Refinement Tests
# ============================================================================

@pytest.mark.asyncio
async def test_refine_with_valid_color_change(suggestion_refiner, mock_openai_client, device_capabilities_rgb):
    """Test refinement with valid RGB color change"""
    # Setup
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "updated_description": "When motion is detected in the Living Room after 6PM, turn on the Living Room Light to blue",
        "changes_made": ["Added color: blue (RGB supported ✓)"],
        "validation": {
            "ok": True,
            "messages": ["✓ Device supports RGB color"],
            "warnings": [],
            "alternatives": [],
        },
        "clarification_needed": None,
    })
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 200
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 250

    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Execute
    result = await suggestion_refiner.refine_description(
        current_description="When motion is detected in the Living Room after 6PM, turn on the Living Room Light to 50% brightness",
        user_input="Make it blue",
        device_capabilities=device_capabilities_rgb,
        conversation_history=[],
    )

    # Assert
    assert "blue" in result.updated_description.lower()
    assert result.validation.ok
    assert len(result.changes_made) > 0
    assert "rgb" in result.changes_made[0].lower() or "color" in result.changes_made[0].lower()


@pytest.mark.asyncio
async def test_refine_with_invalid_color_change(suggestion_refiner, mock_openai_client, device_capabilities_no_rgb):
    """Test refinement when device doesn't support requested feature"""
    # Setup
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "updated_description": "When motion is detected in the Bedroom after 10PM, turn on the Bedroom Light to 50% brightness",
        "changes_made": [],
        "validation": {
            "ok": False,
            "messages": [],
            "warnings": ["⚠️ Bedroom Light does not support RGB color changes"],
            "alternatives": ["Try: 'Set brightness to 75%' or 'Turn on brighter'"],
        },
        "clarification_needed": "This light doesn't support colors. Would you like to adjust brightness instead?",
    })
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 210
    mock_response.usage.completion_tokens = 60
    mock_response.usage.total_tokens = 270

    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Execute
    result = await suggestion_refiner.refine_description(
        current_description="When motion is detected in the Bedroom after 10PM, turn on the Bedroom Light to 50% brightness",
        user_input="Make it blue",
        device_capabilities=device_capabilities_no_rgb,
        conversation_history=[],
    )

    # Assert
    assert not result.validation.ok
    assert len(result.validation.warnings) > 0
    assert "color" in result.validation.warnings[0].lower() or "rgb" in result.validation.warnings[0].lower()
    assert result.clarification_needed is not None


@pytest.mark.asyncio
async def test_refine_with_multiple_changes(suggestion_refiner, mock_openai_client, device_capabilities_rgb):
    """Test refinement with multiple changes at once"""
    # Setup
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "updated_description": "When motion is detected in the Living Room after 6PM on weekdays, turn on the Living Room Light to blue",
        "changes_made": [
            "Added color: blue (RGB supported ✓)",
            "Added condition: weekdays only",
        ],
        "validation": {
            "ok": True,
            "messages": ["✓ Device supports RGB color", "✓ Time condition valid"],
            "warnings": [],
            "alternatives": [],
        },
        "clarification_needed": None,
    })
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 220
    mock_response.usage.completion_tokens = 55
    mock_response.usage.total_tokens = 275

    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Execute
    result = await suggestion_refiner.refine_description(
        current_description="When motion is detected in the Living Room after 6PM, turn on the Living Room Light to 50% brightness",
        user_input="Make it blue and only on weekdays",
        device_capabilities=device_capabilities_rgb,
        conversation_history=[],
    )

    # Assert
    assert "blue" in result.updated_description.lower()
    assert "weekday" in result.updated_description.lower()
    assert len(result.changes_made) == 2
    assert result.validation.ok


# ============================================================================
# Feasibility Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_validate_feasibility_color_supported(suggestion_refiner, device_capabilities_rgb):
    """Test feasibility validation when color is supported"""
    result = await suggestion_refiner.validate_feasibility(
        "Make it blue",
        device_capabilities_rgb,
    )

    assert result.ok
    assert any("rgb" in msg.lower() or "color" in msg.lower() for msg in result.messages)


@pytest.mark.asyncio
async def test_validate_feasibility_color_not_supported(suggestion_refiner, device_capabilities_no_rgb):
    """Test feasibility validation when color is NOT supported"""
    result = await suggestion_refiner.validate_feasibility(
        "Make it blue",
        device_capabilities_no_rgb,
    )

    assert not result.ok
    assert len(result.warnings) > 0
    assert len(result.alternatives) > 0


@pytest.mark.asyncio
async def test_validate_feasibility_brightness_supported(suggestion_refiner, device_capabilities_rgb):
    """Test feasibility validation for brightness"""
    result = await suggestion_refiner.validate_feasibility(
        "Set brightness to 75%",
        device_capabilities_rgb,
    )

    assert result.ok
    assert any("brightness" in msg.lower() for msg in result.messages)


@pytest.mark.asyncio
async def test_validate_feasibility_time_conditions_always_ok(suggestion_refiner, device_capabilities_rgb):
    """Test that time/schedule conditions are always feasible"""
    result = await suggestion_refiner.validate_feasibility(
        "Only on weekdays",
        device_capabilities_rgb,
    )

    assert result.ok
    assert any("time" in msg.lower() or "condition" in msg.lower() for msg in result.messages)


# ============================================================================
# Conversation History Tests
# ============================================================================

@pytest.mark.asyncio
async def test_includes_conversation_history_in_prompt(suggestion_refiner, mock_openai_client, device_capabilities_rgb):
    """Test that conversation history is included in refinement prompt"""
    # Setup
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "updated_description": "Updated description",
        "changes_made": ["Change 3"],
        "validation": {"ok": True, "messages": [], "warnings": [], "alternatives": []},
        "clarification_needed": None,
    })
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 250
    mock_response.usage.completion_tokens = 40
    mock_response.usage.total_tokens = 290

    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Conversation history with 2 previous edits
    history = [
        {
            "user_input": "Make it blue",
            "updated_description": "...turn on light to blue",
            "timestamp": "2025-10-17T18:30:00Z",
        },
        {
            "user_input": "Only on weekdays",
            "updated_description": "...turn on light to blue on weekdays",
            "timestamp": "2025-10-17T18:31:00Z",
        },
    ]

    # Execute
    await suggestion_refiner.refine_description(
        current_description="Current description",
        user_input="Also turn on the fan",
        device_capabilities=device_capabilities_rgb,
        conversation_history=history,
    )

    # Assert - check that OpenAI was called
    assert mock_openai_client.chat.completions.create.called

    # Check that prompt includes history
    call_args = mock_openai_client.chat.completions.create.call_args
    prompt = call_args.kwargs["messages"][1]["content"]
    assert "Make it blue" in prompt  # First edit
    assert "Only on weekdays" in prompt  # Second edit


@pytest.mark.asyncio
async def test_history_entry_created(suggestion_refiner, mock_openai_client, device_capabilities_rgb):
    """Test that refinement creates proper history entry"""
    # Setup
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "updated_description": "New description",
        "changes_made": ["Added color: blue"],
        "validation": {"ok": True, "messages": ["✓ Device supports RGB"], "warnings": [], "alternatives": []},
        "clarification_needed": None,
    })
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 200
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 250

    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Execute
    result = await suggestion_refiner.refine_description(
        current_description="Old description",
        user_input="Make it blue",
        device_capabilities=device_capabilities_rgb,
    )

    # Assert history entry
    assert result.history_entry is not None
    assert result.history_entry["user_input"] == "Make it blue"
    assert result.history_entry["updated_description"] == "New description"
    assert "timestamp" in result.history_entry
    assert result.history_entry["validation_result"]["ok"]


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_refiner_handles_invalid_json(suggestion_refiner, mock_openai_client, device_capabilities_rgb):
    """Test that refiner handles invalid JSON from OpenAI"""
    # Setup - OpenAI returns invalid JSON
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is not JSON!"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 200
    mock_response.usage.completion_tokens = 10
    mock_response.usage.total_tokens = 210

    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Execute - should raise ValueError
    with pytest.raises(ValueError, match="invalid JSON"):
        await suggestion_refiner.refine_description(
            current_description="Current",
            user_input="Change it",
            device_capabilities=device_capabilities_rgb,
        )


@pytest.mark.asyncio
async def test_refiner_retries_on_failure(suggestion_refiner, mock_openai_client, device_capabilities_rgb):
    """Test that refiner retries on API failure"""
    # Setup - fail twice, succeed on third
    success_response = MagicMock()
    success_response.choices = [MagicMock()]
    success_response.choices[0].message.content = json.dumps({
        "updated_description": "Success",
        "changes_made": ["Test"],
        "validation": {"ok": True, "messages": [], "warnings": [], "alternatives": []},
        "clarification_needed": None,
    })
    success_response.usage = MagicMock()
    success_response.usage.prompt_tokens = 200
    success_response.usage.completion_tokens = 30
    success_response.usage.total_tokens = 230

    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=[
            Exception("Timeout"),
            Exception("Rate limit"),
            success_response,
        ],
    )

    # Execute - should succeed after retries
    result = await suggestion_refiner.refine_description(
        current_description="Current",
        user_input="Change it",
        device_capabilities=device_capabilities_rgb,
    )

    # Assert
    assert result.updated_description == "Success"
    assert mock_openai_client.chat.completions.create.call_count == 3


# ============================================================================
# Token Usage Tests
# ============================================================================

@pytest.mark.asyncio
async def test_tracks_token_usage(suggestion_refiner, mock_openai_client, device_capabilities_rgb):
    """Test that token usage is tracked"""
    # Setup
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "updated_description": "Test",
        "changes_made": [],
        "validation": {"ok": True, "messages": [], "warnings": [], "alternatives": []},
        "clarification_needed": None,
    })
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 220
    mock_response.usage.completion_tokens = 45
    mock_response.usage.total_tokens = 265

    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Execute
    await suggestion_refiner.refine_description(
        current_description="Current",
        user_input="Change",
        device_capabilities=device_capabilities_rgb,
    )

    # Assert
    stats = suggestion_refiner.get_usage_stats()
    assert stats["total_tokens"] == 265
    assert stats["input_tokens"] == 220
    assert stats["output_tokens"] == 45
    assert stats["estimated_cost_usd"] > 0

