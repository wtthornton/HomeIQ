"""Tests for Context Analysis Service"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.services.context_analysis_service import ContextAnalysisService
from src.clients.weather_api_client import WeatherAPIClient
from src.clients.sports_data_client import SportsDataClient
from src.clients.carbon_intensity_client import CarbonIntensityClient
from src.clients.data_api_client import DataAPIClient


@pytest.fixture
def mock_weather_client():
    """Mock Weather API client"""
    client = MagicMock(spec=WeatherAPIClient)
    client.get_current_weather = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_sports_client():
    """Mock Sports Data client"""
    client = MagicMock(spec=SportsDataClient)
    client.get_live_games = AsyncMock(return_value=[])
    client.get_upcoming_games = AsyncMock(return_value=[])
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_carbon_client():
    """Mock Carbon Intensity client"""
    client = MagicMock(spec=CarbonIntensityClient)
    client.get_current_intensity = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_data_api_client():
    """Mock Data API client"""
    client = MagicMock(spec=DataAPIClient)
    client.get_events = AsyncMock(return_value=[])
    client.close = AsyncMock()
    return client


@pytest.fixture
def context_service(
    mock_weather_client,
    mock_sports_client,
    mock_carbon_client,
    mock_data_api_client,
):
    """Create ContextAnalysisService with mocked clients"""
    return ContextAnalysisService(
        weather_client=mock_weather_client,
        sports_client=mock_sports_client,
        carbon_client=mock_carbon_client,
        data_api_client=mock_data_api_client,
    )


@pytest.mark.asyncio
async def test_analyze_weather_success(context_service, mock_weather_client):
    """Test successful weather analysis"""
    mock_weather_client.get_current_weather.return_value = {
        "temperature": 75.5,
        "condition": "sunny",
        "humidity": 60,
        "forecast": [
            {"temperature": 78, "condition": "sunny"},
            {"temperature": 80, "condition": "partly_cloudy"},
        ],
    }

    result = await context_service.analyze_weather()

    assert result["available"] is True
    assert result["current"]["temperature"] == 75.5
    assert result["current"]["condition"] == "sunny"
    assert len(result["forecast"]) == 2
    assert result["trends"] is not None


@pytest.mark.asyncio
async def test_analyze_weather_high_temperature(context_service, mock_weather_client):
    """Test weather analysis with high temperature insight"""
    mock_weather_client.get_current_weather.return_value = {
        "temperature": 90,
        "condition": "sunny",
        "humidity": 50,
    }

    result = await context_service.analyze_weather()

    assert result["available"] is True
    assert any("High temperature" in insight for insight in result["insights"])


@pytest.mark.asyncio
async def test_analyze_weather_low_temperature(context_service, mock_weather_client):
    """Test weather analysis with low temperature insight"""
    mock_weather_client.get_current_weather.return_value = {
        "temperature": 40,
        "condition": "cloudy",
        "humidity": 50,
    }

    result = await context_service.analyze_weather()

    assert result["available"] is True
    assert any("Low temperature" in insight for insight in result["insights"])


@pytest.mark.asyncio
async def test_analyze_weather_rainy(context_service, mock_weather_client):
    """Test weather analysis with rainy condition"""
    mock_weather_client.get_current_weather.return_value = {
        "temperature": 65,
        "condition": "rainy",
        "humidity": 80,
    }

    result = await context_service.analyze_weather()

    assert result["available"] is True
    assert any("Rainy conditions" in insight for insight in result["insights"])


@pytest.mark.asyncio
async def test_analyze_weather_unavailable(context_service, mock_weather_client):
    """Test weather analysis when data unavailable"""
    mock_weather_client.get_current_weather.return_value = None

    result = await context_service.analyze_weather()

    assert result["available"] is False
    assert result["current"] is None
    assert result["insights"] == []


@pytest.mark.asyncio
async def test_analyze_sports_success(context_service, mock_sports_client):
    """Test successful sports analysis"""
    mock_sports_client.get_live_games.return_value = [
        {"id": "1", "team": "Lakers", "status": "live"},
    ]
    mock_sports_client.get_upcoming_games.return_value = [
        {"id": "2", "team": "Warriors", "time": "19:00"},
    ]

    result = await context_service.analyze_sports()

    assert result["available"] is True
    assert len(result["live_games"]) == 1
    assert len(result["upcoming_games"]) == 1
    assert len(result["insights"]) > 0


@pytest.mark.asyncio
async def test_analyze_sports_empty(context_service, mock_sports_client):
    """Test sports analysis with no games"""
    mock_sports_client.get_live_games.return_value = []
    mock_sports_client.get_upcoming_games.return_value = []

    result = await context_service.analyze_sports()

    assert result["available"] is True
    assert result["live_games"] == []
    assert result["upcoming_games"] == []


@pytest.mark.asyncio
async def test_analyze_energy_success(context_service, mock_carbon_client):
    """Test successful energy analysis"""
    mock_carbon_client.get_current_intensity.return_value = {
        "intensity": 150,
        "unit": "gCO2/kWh",
    }

    result = await context_service.analyze_energy()

    assert result["available"] is True
    assert result["current_intensity"]["intensity"] == 150
    assert any("Low carbon intensity" in insight for insight in result["insights"])


@pytest.mark.asyncio
async def test_analyze_energy_high_intensity(context_service, mock_carbon_client):
    """Test energy analysis with high carbon intensity"""
    mock_carbon_client.get_current_intensity.return_value = {
        "intensity": 450,
        "unit": "gCO2/kWh",
    }

    result = await context_service.analyze_energy()

    assert result["available"] is True
    assert any("High carbon intensity" in insight for insight in result["insights"])


@pytest.mark.asyncio
async def test_analyze_energy_unavailable(context_service, mock_carbon_client):
    """Test energy analysis when data unavailable"""
    mock_carbon_client.get_current_intensity.return_value = None

    result = await context_service.analyze_energy()

    assert result["available"] is False
    assert result["current_intensity"] is None


@pytest.mark.asyncio
async def test_analyze_historical_patterns_success(context_service, mock_data_api_client):
    """Test successful historical pattern analysis"""
    now = datetime.utcnow()
    events = [
        {
            "entity_id": "light.living_room",
            "state": "on",
            "timestamp": (now - timedelta(hours=1)).isoformat(),
        },
        {
            "entity_id": "light.living_room",
            "state": "off",
            "timestamp": (now - timedelta(hours=2)).isoformat(),
        },
        {
            "entity_id": "light.kitchen",
            "state": "on",
            "timestamp": (now - timedelta(hours=3)).isoformat(),
        },
    ]

    mock_data_api_client.get_events.return_value = events

    result = await context_service.analyze_historical_patterns(days_back=7)

    assert result["available"] is True
    assert result["events_count"] == 3
    assert len(result["patterns"]) > 0
    assert "frequent_entities" in [p["type"] for p in result["patterns"]]


@pytest.mark.asyncio
async def test_analyze_historical_patterns_empty(context_service, mock_data_api_client):
    """Test historical pattern analysis with no events"""
    mock_data_api_client.get_events.return_value = []

    result = await context_service.analyze_historical_patterns()

    assert result["available"] is False
    assert result["events"] == []
    assert result["patterns"] == []


@pytest.mark.asyncio
async def test_analyze_all_context(context_service):
    """Test comprehensive context analysis"""
    # Setup mocks
    context_service.weather_client.get_current_weather = AsyncMock(
        return_value={"temperature": 75, "condition": "sunny"}
    )
    context_service.sports_client.get_live_games = AsyncMock(return_value=[])
    context_service.sports_client.get_upcoming_games = AsyncMock(return_value=[])
    context_service.carbon_client.get_current_intensity = AsyncMock(return_value=None)
    context_service.data_api_client.get_events = AsyncMock(return_value=[])

    result = await context_service.analyze_all_context()

    assert "weather" in result
    assert "sports" in result
    assert "energy" in result
    assert "historical_patterns" in result
    assert "summary" in result
    assert "timestamp" in result
    assert result["summary"]["total_sources"] == 4


@pytest.mark.asyncio
async def test_close_clients(context_service):
    """Test that all clients are closed properly"""
    await context_service.close()

    context_service.weather_client.close.assert_called_once()
    context_service.sports_client.close.assert_called_once()
    context_service.carbon_client.close.assert_called_once()
    context_service.data_api_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_weather_trends_analysis(context_service):
    """Test weather trend analysis"""
    forecast = [
        {"temperature": 70},
        {"temperature": 75},
        {"temperature": 80},
        {"temperature": 78},
    ]

    trends = context_service._analyze_weather_trends(forecast)

    assert trends is not None
    assert trends["average_temperature"] > 0
    assert trends["max_temperature"] == 80
    assert trends["min_temperature"] == 70
    assert trends["trend"] == "increasing"


@pytest.mark.asyncio
async def test_detect_patterns(context_service):
    """Test pattern detection"""
    events = [
        {"entity_id": "light.living_room", "state": "on"},
        {"entity_id": "light.living_room", "state": "off"},
        {"entity_id": "light.living_room", "state": "on"},
        {"entity_id": "light.kitchen", "state": "on"},
    ]

    patterns = context_service._detect_patterns(events)

    assert len(patterns) > 0
    assert any(p["type"] == "frequent_entities" for p in patterns)


@pytest.mark.asyncio
async def test_detect_time_patterns(context_service):
    """Test time-based pattern detection"""
    now = datetime.utcnow()
    events = [
        {"entity_id": "light.living_room", "timestamp": now.isoformat()},
        {"entity_id": "light.kitchen", "timestamp": now.isoformat()},
        {
            "entity_id": "light.bedroom",
            "timestamp": (now - timedelta(hours=1)).isoformat(),
        },
    ]

    patterns = context_service._detect_time_patterns(events)

    assert len(patterns) > 0
    assert any(p["type"] == "peak_hours" for p in patterns)

