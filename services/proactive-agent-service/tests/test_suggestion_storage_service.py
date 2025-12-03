"""Tests for Suggestion Storage Service"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.services.suggestion_storage_service import SuggestionStorageService
from src.models import Suggestion


@pytest.fixture
async def storage_service(mock_db_session):
    """Create SuggestionStorageService instance with mock DB"""
    service = SuggestionStorageService()
    return service


@pytest.mark.asyncio
async def test_create_suggestion(storage_service, mock_db_session):
    """Test creating a suggestion"""
    suggestion = await storage_service.create_suggestion(
        prompt="Test prompt",
        context_type="weather",
        quality_score=0.8,
        db=mock_db_session,
    )

    assert suggestion is not None
    assert suggestion.prompt == "Test prompt"
    assert suggestion.context_type == "weather"
    assert suggestion.status == "pending"
    assert suggestion.quality_score == 0.8


@pytest.mark.asyncio
async def test_get_suggestion(storage_service, mock_db_session):
    """Test getting a suggestion by ID"""
    # Create first
    created = await storage_service.create_suggestion(
        prompt="Test prompt",
        context_type="weather",
        db=mock_db_session,
    )

    # Get it
    retrieved = await storage_service.get_suggestion(created.id, db=mock_db_session)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.prompt == "Test prompt"


@pytest.mark.asyncio
async def test_list_suggestions(storage_service, mock_db_session):
    """Test listing suggestions"""
    # Create multiple
    await storage_service.create_suggestion("Prompt 1", "weather", db=mock_db_session)
    await storage_service.create_suggestion("Prompt 2", "sports", db=mock_db_session)

    # List all
    suggestions = await storage_service.list_suggestions(db=mock_db_session)

    assert len(suggestions) >= 2


@pytest.mark.asyncio
async def test_update_suggestion_status(storage_service, mock_db_session):
    """Test updating suggestion status"""
    # Create
    suggestion = await storage_service.create_suggestion(
        "Test prompt",
        "weather",
        db=mock_db_session,
    )

    # Update status
    updated = await storage_service.update_suggestion_status(
        suggestion.id,
        "sent",
        agent_response={"message": "Response"},
        db=mock_db_session,
    )

    assert updated is not None
    assert updated.status == "sent"
    assert updated.agent_response == {"message": "Response"}
    assert updated.sent_at is not None


@pytest.mark.asyncio
async def test_delete_suggestion(storage_service, mock_db_session):
    """Test deleting a suggestion"""
    # Create
    suggestion = await storage_service.create_suggestion(
        "Test prompt",
        "weather",
        db=mock_db_session,
    )

    # Delete
    deleted = await storage_service.delete_suggestion(suggestion.id, db=mock_db_session)

    assert deleted is True

    # Verify deleted
    retrieved = await storage_service.get_suggestion(suggestion.id, db=mock_db_session)
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_suggestion_stats(storage_service, mock_db_session):
    """Test getting suggestion statistics"""
    # Create suggestions with different statuses
    await storage_service.create_suggestion("Prompt 1", "weather", db=mock_db_session)
    await storage_service.create_suggestion("Prompt 2", "sports", db=mock_db_session)

    stats = await storage_service.get_suggestion_stats(db=mock_db_session)

    assert "total" in stats
    assert "by_status" in stats
    assert "by_context_type" in stats
    assert stats["total"] >= 2

