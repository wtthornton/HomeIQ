"""
Tests for Suggestion Pipeline Service
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.services.suggestion_pipeline_service import (
    SuggestionPipelineService,
)


@pytest.fixture
def mock_context_service():
    """Create mock context analysis service"""
    service = MagicMock()
    service.analyze_all_context = AsyncMock(
        return_value={
            "weather": {"available": True, "current": {"temperature": 75}},
            "timestamp": "2025-01-07T12:00:00Z",
        }
    )
    return service


@pytest.fixture
def mock_prompt_service():
    """Create mock prompt generation service"""
    service = MagicMock()
    service.generate_prompts = MagicMock(
        return_value=[
            {
                "prompt": "Test prompt",
                "context_type": "weather",
                "quality_score": 0.8,
                "metadata": {},
            }
        ]
    )
    return service


@pytest.fixture
def mock_agent_client():
    """Create mock HA agent client"""
    client = MagicMock()
    client.send_message = AsyncMock(
        return_value={
            "message": "Agent response",
            "conversation_id": "conv-123",
        }
    )
    return client


@pytest.fixture
def mock_storage_service():
    """Create mock storage service"""
    from datetime import datetime

    from src.models import Suggestion

    service = MagicMock()
    suggestion = Suggestion(
        id="test-id",
        prompt="Test prompt",
        context_type="weather",
        status="pending",
        quality_score=0.8,
        created_at=datetime.now(UTC),
    )
    service.create_suggestion = AsyncMock(return_value=suggestion)
    service.update_suggestion_status = AsyncMock(return_value=suggestion)
    return service


@pytest.mark.asyncio
async def test_generate_suggestions_handles_prompt_generation_failure(
    mock_context_service,
    mock_agent_client,
    mock_storage_service,
):
    """Test that generate_suggestions handles prompt generation failure gracefully"""
    # Create a prompt service that raises an exception
    mock_prompt_service = MagicMock()
    mock_prompt_service.generate_prompts = MagicMock(
        side_effect=Exception("Prompt generation failed")
    )

    pipeline = SuggestionPipelineService(
        context_service=mock_context_service,
        prompt_service=mock_prompt_service,
        agent_client=mock_agent_client,
        storage_service=mock_storage_service,
    )

    result = await pipeline.generate_suggestions()

    assert result["success"] is False
    assert result["suggestions_created"] == 0
    assert len(result["details"]) > 0
    assert result["details"][0]["step"] == "prompt_generation"
    assert "error" in result["details"][0]


@pytest.mark.asyncio
async def test_generate_suggestions_handles_storage_failure(
    mock_context_service,
    mock_prompt_service,
    mock_agent_client,
):
    """Test that generate_suggestions handles storage failure gracefully"""
    # Create a storage service that raises an exception
    mock_storage_service = MagicMock()
    mock_storage_service.create_suggestion = AsyncMock(side_effect=Exception("Storage failed"))

    pipeline = SuggestionPipelineService(
        context_service=mock_context_service,
        prompt_service=mock_prompt_service,
        agent_client=mock_agent_client,
        storage_service=mock_storage_service,
    )

    result = await pipeline.generate_suggestions()

    # Storage failure should be caught and logged, but pipeline should continue
    # The suggestion creation count should be 0 due to the failure
    assert result["suggestions_created"] == 0
    assert result["suggestions_failed"] > 0
    assert any(detail.get("step") == "prompt_processing" for detail in result["details"])


@pytest.mark.asyncio
async def test_generate_suggestions_handles_agent_communication_failure(
    mock_context_service,
    mock_prompt_service,
    mock_storage_service,
):
    """Test that generate_suggestions handles agent communication failure gracefully"""
    # Create an agent client that raises an exception
    mock_agent_client = MagicMock()
    mock_agent_client.send_message = AsyncMock(side_effect=Exception("Agent communication failed"))

    pipeline = SuggestionPipelineService(
        context_service=mock_context_service,
        prompt_service=mock_prompt_service,
        agent_client=mock_agent_client,
        storage_service=mock_storage_service,
    )

    result = await pipeline.generate_suggestions()

    # Suggestion should be created, but not sent
    assert result["suggestions_created"] > 0
    assert result["suggestions_sent"] == 0
    assert result["suggestions_failed"] > 0
    assert any(detail.get("step") == "agent_communication" for detail in result["details"])


@pytest.mark.asyncio
async def test_generate_suggestions_handles_none_context_analysis(
    mock_prompt_service,
    mock_agent_client,
    mock_storage_service,
):
    """Test that generate_suggestions handles None context analysis gracefully"""
    # Create a context service that returns None
    mock_context_service = MagicMock()
    mock_context_service.analyze_all_context = AsyncMock(return_value=None)

    pipeline = SuggestionPipelineService(
        context_service=mock_context_service,
        prompt_service=mock_prompt_service,
        agent_client=mock_agent_client,
        storage_service=mock_storage_service,
    )

    result = await pipeline.generate_suggestions()

    assert result["success"] is False
    assert result["suggestions_created"] == 0
    assert len(result["details"]) > 0
    assert result["details"][0]["step"] == "context_analysis"
    assert result["details"][0]["error"] == "No context available"


def _make_pipeline(
    mock_context_service, mock_prompt_service, mock_agent_client, mock_storage_service
):
    return SuggestionPipelineService(
        context_service=mock_context_service,
        prompt_service=mock_prompt_service,
        agent_client=mock_agent_client,
        storage_service=mock_storage_service,
    )


def test_filter_by_timing_filters_candidate_in_earlier_quiet_window(
    mock_context_service, mock_prompt_service, mock_agent_client, mock_storage_service
):
    """A candidate inside an EARLIER quiet window must be filtered even when a
    LATER quiet window in the same list doesn't match (union semantics)."""
    pipeline = _make_pipeline(
        mock_context_service, mock_prompt_service, mock_agent_client, mock_storage_service
    )

    candidates = [{"prompt": "Turn down the thermostat"}]
    timing_context = {
        "quiet_hours": [
            {"start": "22:00", "end": "07:00"},  # overnight window; matches hour 23
            {"start": "13:00", "end": "14:00"},  # does not match hour 23
        ]
    }

    with patch("src.services.suggestion_pipeline_service.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 7, 23, 0, tzinfo=UTC)
        filtered = pipeline._filter_by_timing(candidates, timing_context)

    assert filtered == []


def test_filter_by_timing_is_order_independent(
    mock_context_service, mock_prompt_service, mock_agent_client, mock_storage_service
):
    """Swapping the order of the two quiet windows must not change the result."""
    pipeline = _make_pipeline(
        mock_context_service, mock_prompt_service, mock_agent_client, mock_storage_service
    )

    candidates = [{"prompt": "Turn down the thermostat"}]
    timing_context = {
        "quiet_hours": [
            {"start": "13:00", "end": "14:00"},  # does not match hour 23
            {"start": "22:00", "end": "07:00"},  # overnight window; matches hour 23
        ]
    }

    with patch("src.services.suggestion_pipeline_service.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 7, 23, 0, tzinfo=UTC)
        filtered = pipeline._filter_by_timing(candidates, timing_context)

    assert filtered == []
