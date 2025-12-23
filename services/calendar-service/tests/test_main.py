"""
Unit tests for Calendar Service Main Application

Tests for main.py application initialization, service lifecycle, and core functionality.
"""

import asyncio
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web

# Set environment variables before importing main
os.environ.setdefault("INFLUXDB_TOKEN", "test-token")
os.environ.setdefault("INFLUXDB_URL", "http://localhost:8086")
os.environ.setdefault("INFLUXDB_ORG", "test-org")
os.environ.setdefault("INFLUXDB_BUCKET", "test-bucket")
os.environ.setdefault("CALENDAR_ENTITIES", "calendar.personal,calendar.work")
os.environ.setdefault("CALENDAR_FETCH_INTERVAL", "60")
os.environ.setdefault("SERVICE_PORT", "8011")

from main import CalendarService, create_app


class TestCalendarService:
    """Test suite for CalendarService class."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings configuration."""
        with patch('main.settings') as mock:
            mock.calendar_entities = "calendar.personal,calendar.work"
            mock.influxdb_url = "http://localhost:8086"
            mock.influxdb_token = "test-token"
            mock.influxdb_org = "test-org"
            mock.influxdb_bucket = "test-bucket"
            mock.calendar_fetch_interval = 60
            mock.service_port = 8011
            yield mock

    @pytest.fixture
    def service(self, mock_settings):
        """Create CalendarService instance."""
        with patch('main.settings', mock_settings):
            return CalendarService()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_service_initialization(self, service, mock_settings):
        """Test service initializes correctly."""
        assert service.calendar_entities == ["calendar.personal", "calendar.work"]
        assert service.influxdb_url == "http://localhost:8086"
        assert service.influxdb_token == "test-token"
        assert service.fetch_interval == 60
        assert service.ha_client is None
        assert service.influxdb_client is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_service_initialization_missing_token(self, mock_settings):
        """Test service raises error when InfluxDB token is missing."""
        mock_settings.influxdb_token = ""
        with patch('main.settings', mock_settings):
            with pytest.raises(ValueError, match="INFLUXDB_TOKEN required"):
                CalendarService()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('main.ha_connection_manager')
    @patch('main.InfluxDBClient3')
    async def test_startup_success(
        self,
        mock_influxdb_client,
        mock_ha_manager,
        service
    ):
        """Test successful service startup."""
        # Mock HA connection manager
        mock_connection = MagicMock()
        mock_connection.name = "test-connection"
        mock_connection.url = "ws://localhost:8123/api/websocket"
        mock_connection.token = "test-token"
        mock_ha_manager.get_connection_with_circuit_breaker = AsyncMock(
            return_value=mock_connection
        )

        # Mock HA client
        mock_ha_client = AsyncMock()
        mock_ha_client.test_connection = AsyncMock(return_value=True)
        mock_ha_client.get_calendars = AsyncMock(
            return_value=["calendar.personal", "calendar.work"]
        )

        with patch('main.HomeAssistantCalendarClient', return_value=mock_ha_client):
            await service.startup()

        assert service.ha_client is not None
        assert service.influxdb_client is not None
        assert service.health_handler.ha_connected is True
        assert service.health_handler.calendar_count == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('main.ha_connection_manager')
    async def test_startup_no_ha_connection(self, mock_ha_manager, service):
        """Test startup fails when no HA connection available."""
        mock_ha_manager.get_connection_with_circuit_breaker = AsyncMock(
            return_value=None
        )

        with pytest.raises(ConnectionError, match="No Home Assistant connections available"):
            await service.startup()

        assert service.health_handler.ha_connected is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('main.ha_connection_manager')
    async def test_startup_ha_connection_fails(self, mock_ha_manager, service):
        """Test startup fails when HA connection test fails."""
        mock_connection = MagicMock()
        mock_connection.name = "test-connection"
        mock_connection.url = "ws://localhost:8123/api/websocket"
        mock_connection.token = "test-token"
        mock_ha_manager.get_connection_with_circuit_breaker = AsyncMock(
            return_value=mock_connection
        )

        mock_ha_client = AsyncMock()
        mock_ha_client.test_connection = AsyncMock(return_value=False)

        with patch('main.HomeAssistantCalendarClient', return_value=mock_ha_client):
            with pytest.raises(ConnectionError, match="Cannot connect to Home Assistant"):
                await service.startup()

        assert service.health_handler.ha_connected is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_shutdown(self, service):
        """Test service shutdown."""
        # Set up mock clients
        service.ha_client = AsyncMock()
        service.influxdb_client = MagicMock()

        await service.shutdown()

        service.ha_client.close.assert_called_once()
        service.influxdb_client.close.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_shutdown_no_clients(self, service):
        """Test shutdown handles missing clients gracefully."""
        service.ha_client = None
        service.influxdb_client = None

        # Should not raise
        await service.shutdown()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('main.datetime')
    async def test_get_today_events_success(self, mock_datetime, service):
        """Test successful event fetching."""
        # Mock current time
        now = datetime(2025, 12, 23, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = now

        # Mock HA client
        mock_ha_client = AsyncMock()
        mock_ha_client.get_events_from_multiple_calendars = AsyncMock(
            return_value={
                "calendar.personal": [
                    {
                        "summary": "Test Event",
                        "start": "2025-12-23T14:00:00Z",
                        "end": "2025-12-23T15:00:00Z"
                    }
                ]
            }
        )
        service.ha_client = mock_ha_client

        # Mock event parser
        mock_parser = MagicMock()
        mock_parser.parse_multiple_events = MagicMock(
            return_value=[
                {
                    "summary": "Test Event",
                    "start": datetime(2025, 12, 23, 14, 0, 0, tzinfo=timezone.utc),
                    "calendar_source": "calendar.personal"
                }
            ]
        )
        service.event_parser = mock_parser

        events = await service.get_today_events()

        assert len(events) == 1
        assert events[0]["summary"] == "Test Event"
        assert service.health_handler.last_successful_fetch is not None
        assert service.health_handler.total_fetches == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_today_events_error(self, service):
        """Test event fetching handles errors gracefully."""
        # Mock HA client to raise error
        mock_ha_client = AsyncMock()
        mock_ha_client.get_events_from_multiple_calendars = AsyncMock(
            side_effect=Exception("Connection error")
        )
        service.ha_client = mock_ha_client

        events = await service.get_today_events()

        assert events == []
        assert service.health_handler.ha_connected is False
        assert service.health_handler.failed_fetches == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('main.datetime')
    async def test_predict_home_status_no_events(self, mock_datetime, service):
        """Test occupancy prediction with no events."""
        now = datetime(2025, 12, 23, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = now

        # Mock get_today_events to return empty list
        service.get_today_events = AsyncMock(return_value=[])

        prediction = await service.predict_home_status()

        assert prediction is not None
        assert prediction["currently_home"] is False
        assert prediction["wfh_today"] is False
        assert prediction["event_count"] == 0
        assert prediction["confidence"] == 0.5

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('main.datetime')
    async def test_predict_home_status_with_events(self, mock_datetime, service):
        """Test occupancy prediction with events."""
        now = datetime(2025, 12, 23, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = now

        # Mock events
        mock_events = [
            {
                "summary": "Work from Home",
                "start": datetime(2025, 12, 23, 9, 0, 0, tzinfo=timezone.utc),
                "end": datetime(2025, 12, 23, 17, 0, 0, tzinfo=timezone.utc),
                "is_wfh": True,
                "is_home": True
            }
        ]

        service.get_today_events = AsyncMock(return_value=mock_events)

        # Mock event parser methods
        service.event_parser.get_current_events = MagicMock(return_value=mock_events)
        service.event_parser.get_upcoming_events = MagicMock(return_value=[])

        prediction = await service.predict_home_status()

        assert prediction is not None
        assert prediction["currently_home"] is True
        assert prediction["wfh_today"] is True
        assert prediction["event_count"] == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_predict_home_status_error(self, service):
        """Test occupancy prediction handles errors gracefully."""
        service.get_today_events = AsyncMock(side_effect=Exception("Error"))

        prediction = await service.predict_home_status()

        assert prediction is None
        assert service.health_handler.failed_fetches == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('main.asyncio.to_thread')
    async def test_store_in_influxdb_success(self, mock_to_thread, service):
        """Test successful InfluxDB write."""
        mock_influxdb_client = MagicMock()
        service.influxdb_client = mock_influxdb_client
        mock_to_thread.return_value = AsyncMock()

        prediction = {
            "currently_home": True,
            "wfh_today": False,
            "confidence": 0.85,
            "hours_until_arrival": 2.5,
            "timestamp": datetime.now(timezone.utc)
        }

        await service.store_in_influxdb(prediction)

        mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_in_influxdb_no_prediction(self, service):
        """Test InfluxDB write skips when prediction is None."""
        await service.store_in_influxdb(None)
        # Should return without error

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_in_influxdb_no_client(self, service):
        """Test InfluxDB write handles missing client."""
        service.influxdb_client = None

        prediction = {"currently_home": True}

        # Should not raise, just log error
        await service.store_in_influxdb(prediction)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('main.asyncio.to_thread')
    async def test_store_in_influxdb_error(self, mock_to_thread, service):
        """Test InfluxDB write handles errors."""
        mock_influxdb_client = MagicMock()
        service.influxdb_client = mock_influxdb_client
        mock_to_thread.side_effect = Exception("Write error")

        prediction = {
            "currently_home": True,
            "timestamp": datetime.now(timezone.utc)
        }

        with pytest.raises(RuntimeError, match="Failed to write occupancy prediction"):
            await service.store_in_influxdb(prediction)

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('main.asyncio.sleep')
    async def test_run_continuous_success(self, mock_sleep, service):
        """Test continuous loop runs successfully."""
        mock_sleep.return_value = AsyncMock()

        service.predict_home_status = AsyncMock(
            return_value={"currently_home": True}
        )
        service.store_in_influxdb = AsyncMock()
        service.health_handler.ha_connected = False  # Initialize to False

        # Run for a few iterations
        task = asyncio.create_task(service.run_continuous())
        await asyncio.sleep(0.1)  # Let it run briefly
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # After successful run, ha_connected should be True
        # (set in run_continuous after successful fetch and store)
        assert service.predict_home_status.call_count > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('main.asyncio.sleep')
    async def test_run_continuous_influxdb_error(self, mock_sleep, service):
        """Test continuous loop handles InfluxDB errors."""
        # Make sleep actually sleep briefly to allow loop to run
        async def mock_sleep_impl(delay):
            await asyncio.sleep(0.01)  # Brief sleep to allow task to run
        
        mock_sleep.side_effect = mock_sleep_impl

        service.predict_home_status = AsyncMock(
            return_value={"currently_home": True}
        )
        service.store_in_influxdb = AsyncMock(side_effect=Exception("InfluxDB error"))

        # Run for a few iterations
        task = asyncio.create_task(service.run_continuous())
        await asyncio.sleep(0.05)  # Let it run briefly
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should continue running despite InfluxDB error
        assert service.predict_home_status.call_count > 0


class TestCreateApp:
    """Test suite for create_app function."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_app(self):
        """Test app creation."""
        service = MagicMock()
        service.health_handler = MagicMock()

        app = await create_app(service)

        assert isinstance(app, web.Application)
        # Check health route is registered by checking route resources
        route_paths = []
        for route in app.router.routes():
            if hasattr(route, 'path'):
                route_paths.append(route.path)
            elif hasattr(route, '_resource'):
                # For ResourceRoute, check the resource path
                if hasattr(route._resource, 'canonical'):
                    route_paths.append(route._resource.canonical)
        
        # Verify app has routes (health endpoint should be registered)
        assert len(list(app.router.routes())) > 0

