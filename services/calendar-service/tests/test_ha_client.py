"""
Unit tests for Home Assistant Calendar Client
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import aiohttp
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from ha_client import HomeAssistantCalendarClient


@pytest.fixture
def mock_session():
    """Create mock aiohttp session"""
    session = MagicMock()
    return session


@pytest.fixture
def ha_client():
    """Create HA client instance"""
    return HomeAssistantCalendarClient(
        base_url="http://localhost:8123",
        token="test_token"
    )


@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization"""
    client = HomeAssistantCalendarClient(
        base_url="http://localhost:8123/",  # With trailing slash
        token="test_token"
    )
    
    assert client.base_url == "http://localhost:8123"
    assert client.token == "test_token"
    assert client.session is None


@pytest.mark.asyncio
async def test_connect(ha_client):
    """Test session connection"""
    await ha_client.connect()
    
    assert ha_client.session is not None
    assert isinstance(ha_client.session, aiohttp.ClientSession)
    
    await ha_client.close()


@pytest.mark.asyncio
async def test_close(ha_client):
    """Test session closure"""
    await ha_client.connect()
    assert ha_client.session is not None
    
    await ha_client.close()
    assert ha_client.session is None


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager"""
    async with HomeAssistantCalendarClient("http://localhost:8123", "token") as client:
        assert client.session is not None
    
    # Session should be closed after context
    assert client.session is None


@pytest.mark.asyncio
async def test_test_connection_success(ha_client):
    """Test successful connection test"""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"message": "API running."})
    
    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock()
    
    ha_client.session = MagicMock()
    ha_client.session.get = MagicMock(return_value=mock_session)
    
    result = await ha_client.test_connection()
    
    assert result is True


@pytest.mark.asyncio
async def test_test_connection_failure(ha_client):
    """Test failed connection test"""
    mock_response = AsyncMock()
    mock_response.status = 500
    
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock()
    
    ha_client.session = MagicMock()
    ha_client.session.get = MagicMock(return_value=mock_session)
    
    result = await ha_client.test_connection()
    
    assert result is False


@pytest.mark.asyncio
async def test_get_calendars(ha_client):
    """Test getting calendar list"""
    mock_states = [
        {"entity_id": "calendar.primary", "state": "off"},
        {"entity_id": "calendar.work", "state": "on"},
        {"entity_id": "sensor.temperature", "state": "20"},
        {"entity_id": "calendar.personal", "state": "off"},
    ]
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_states)
    
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock()
    
    ha_client.session = MagicMock()
    ha_client.session.get = MagicMock(return_value=mock_session)
    
    calendars = await ha_client.get_calendars()
    
    assert len(calendars) == 3
    assert "calendar.primary" in calendars
    assert "calendar.work" in calendars
    assert "calendar.personal" in calendars
    assert "sensor.temperature" not in calendars


@pytest.mark.asyncio
async def test_get_calendars_empty(ha_client):
    """Test getting calendars when none exist"""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=[])
    
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock()
    
    ha_client.session = MagicMock()
    ha_client.session.get = MagicMock(return_value=mock_session)
    
    calendars = await ha_client.get_calendars()
    
    assert calendars == []


@pytest.mark.asyncio
async def test_get_events(ha_client):
    """Test getting calendar events"""
    mock_events = [
        {
            "summary": "Team Meeting",
            "start": {"dateTime": "2025-10-16T14:00:00-07:00"},
            "end": {"dateTime": "2025-10-16T15:00:00-07:00"},
            "location": "Conference Room"
        },
        {
            "summary": "Lunch",
            "start": {"dateTime": "2025-10-16T12:00:00-07:00"},
            "end": {"dateTime": "2025-10-16T13:00:00-07:00"}
        }
    ]
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_events)
    
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock()
    
    ha_client.session = MagicMock()
    ha_client.session.get = MagicMock(return_value=mock_session)
    
    start = datetime(2025, 10, 16, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 10, 16, 23, 59, 59, tzinfo=timezone.utc)
    
    events = await ha_client.get_events("calendar.primary", start, end)
    
    assert len(events) == 2
    assert events[0]["summary"] == "Team Meeting"
    assert events[1]["summary"] == "Lunch"


@pytest.mark.asyncio
async def test_get_events_with_prefix(ha_client):
    """Test getting events with calendar. prefix"""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=[])
    
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock()
    
    ha_client.session = MagicMock()
    ha_client.session.get = MagicMock(return_value=mock_session)
    
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=1)
    
    # Should work with or without prefix
    await ha_client.get_events("calendar.primary", start, end)
    await ha_client.get_events("primary", start, end)


@pytest.mark.asyncio
async def test_get_events_not_found(ha_client):
    """Test getting events from non-existent calendar"""
    mock_response = AsyncMock()
    mock_response.status = 404
    
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock()
    
    ha_client.session = MagicMock()
    ha_client.session.get = MagicMock(return_value=mock_session)
    
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=1)
    
    events = await ha_client.get_events("nonexistent", start, end)
    
    assert events == []


@pytest.mark.asyncio
async def test_get_calendar_state(ha_client):
    """Test getting calendar state"""
    mock_state = {
        "entity_id": "calendar.primary",
        "state": "on",
        "attributes": {
            "message": "Team Meeting",
            "all_day": False,
            "start_time": "2025-10-16 14:00:00",
            "end_time": "2025-10-16 15:00:00"
        }
    }
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_state)
    
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock()
    
    ha_client.session = MagicMock()
    ha_client.session.get = MagicMock(return_value=mock_session)
    
    state = await ha_client.get_calendar_state("calendar.primary")
    
    assert state is not None
    assert state["entity_id"] == "calendar.primary"
    assert state["state"] == "on"
    assert state["attributes"]["message"] == "Team Meeting"


@pytest.mark.asyncio
async def test_get_events_from_multiple_calendars(ha_client):
    """Test getting events from multiple calendars concurrently"""
    
    async def mock_get_events(calendar_id, start, end):
        if calendar_id == "calendar.primary":
            return [{"summary": "Event 1"}]
        elif calendar_id == "calendar.work":
            return [{"summary": "Event 2"}, {"summary": "Event 3"}]
        return []
    
    ha_client.get_events = mock_get_events
    
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=1)
    
    results = await ha_client.get_events_from_multiple_calendars(
        ["calendar.primary", "calendar.work"],
        start,
        end
    )
    
    assert len(results) == 2
    assert len(results["calendar.primary"]) == 1
    assert len(results["calendar.work"]) == 2


@pytest.mark.asyncio
async def test_get_events_from_multiple_calendars_with_error(ha_client):
    """Test getting events from multiple calendars with one failing"""
    
    async def mock_get_events(calendar_id, start, end):
        if calendar_id == "calendar.primary":
            return [{"summary": "Event 1"}]
        elif calendar_id == "calendar.error":
            raise Exception("Calendar error")
        return []
    
    ha_client.get_events = mock_get_events
    
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=1)
    
    results = await ha_client.get_events_from_multiple_calendars(
        ["calendar.primary", "calendar.error"],
        start,
        end
    )
    
    assert len(results) == 2
    assert len(results["calendar.primary"]) == 1
    assert len(results["calendar.error"]) == 0  # Error returns empty list

