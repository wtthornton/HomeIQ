"""
Unit tests for HealthCheckHandler - Critical monitoring component
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from health_check import HealthCheckHandler


class TestHealthCheckHandlerInitialization:
    """Test health check handler initialization"""

    def test_init(self):
        """Test initialization"""
        handler = HealthCheckHandler()

        assert handler.start_time is not None
        assert isinstance(handler.start_time, datetime)
        assert handler.connection_manager is None
        assert handler.historical_counter is None


class TestHealthCheckHandlerConfiguration:
    """Test health check handler configuration"""

    def test_set_connection_manager(self):
        """Test setting connection manager"""
        handler = HealthCheckHandler()
        mock_manager = Mock()

        handler.set_connection_manager(mock_manager)

        assert handler.connection_manager == mock_manager

    def test_set_historical_counter(self):
        """Test setting historical counter"""
        handler = HealthCheckHandler()
        mock_counter = Mock()

        handler.set_historical_counter(mock_counter)

        assert handler.historical_counter == mock_counter


class TestHealthCheckHandlerBasicHealth:
    """Test basic health check functionality"""

    @pytest.mark.asyncio
    async def test_handle_basic_health_check(self):
        """Test basic health check without dependencies"""
        handler = HealthCheckHandler()
        mock_request = Mock()

        response = await handler.handle(mock_request)

        assert response.status == 200
        assert response.content_type == "application/json"

    @pytest.mark.asyncio
    async def test_health_check_response_structure(self):
        """Test health check response has required fields"""
        handler = HealthCheckHandler()
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert "status" in data
        assert "service" in data
        assert "uptime" in data
        assert "timestamp" in data
        assert data["service"] == "websocket-ingestion"
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_health_check_without_connection_manager(self):
        """Test health check when connection manager is not set"""
        handler = HealthCheckHandler()
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert data["status"] == "degraded"
        assert "reason" in data
        assert data["reason"] == "Connection manager not initialized"
        assert data["connection"]["status"] == "not_initialized"
        assert data["subscription"]["status"] == "not_initialized"


class TestHealthCheckHandlerWithConnectionManager:
    """Test health check with connection manager"""

    @pytest.mark.asyncio
    async def test_health_check_with_running_connection(self):
        """Test health check with running connection manager"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = True
        mock_manager.connection_attempts = 5
        mock_manager.successful_connections = 4
        mock_manager.failed_connections = 1
        mock_manager.event_subscription = None

        handler.set_connection_manager(mock_manager)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert data["status"] == "degraded"  # No subscription
        assert "connection" in data
        assert data["connection"]["is_running"] is True
        assert data["connection"]["connection_attempts"] == 5
        assert data["connection"]["successful_connections"] == 4
        assert data["connection"]["failed_connections"] == 1

    @pytest.mark.asyncio
    async def test_health_check_with_not_running_connection(self):
        """Test health check when connection is not running"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = False
        mock_manager.connection_attempts = 0
        mock_manager.successful_connections = 0
        mock_manager.failed_connections = 0

        handler.set_connection_manager(mock_manager)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert data["status"] == "unhealthy"
        assert data["reason"] == "Connection manager not running"

    @pytest.mark.asyncio
    async def test_health_check_with_multiple_failures(self):
        """Test health check with multiple connection failures"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = True
        mock_manager.connection_attempts = 10
        mock_manager.successful_connections = 3
        mock_manager.failed_connections = 7
        mock_manager.event_subscription = None

        handler.set_connection_manager(mock_manager)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert data["status"] == "degraded"
        assert data["reason"] == "Multiple connection failures"


class TestHealthCheckHandlerWithSubscription:
    """Test health check with event subscription"""

    @pytest.mark.asyncio
    async def test_health_check_with_active_subscription(self):
        """Test health check with active event subscription"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = True
        mock_manager.connection_attempts = 1
        mock_manager.successful_connections = 1
        mock_manager.failed_connections = 0

        mock_subscription = Mock()
        mock_subscription.is_subscribed = True
        mock_subscription.total_events_received = 100
        mock_subscription.subscription_start_time = datetime.now() - timedelta(minutes=10)

        def get_subscription_status():
            return {
                "is_subscribed": True,
                "active_subscriptions": 1,
                "total_events_received": 100,
                "events_by_type": {"state_changed": 90, "service_registered": 10},
                "last_event_time": datetime.now().isoformat(),
                "subscription_start_time": mock_subscription.subscription_start_time.isoformat()
            }

        mock_subscription.get_subscription_status = get_subscription_status
        mock_manager.event_subscription = mock_subscription

        handler.set_connection_manager(mock_manager)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert data["status"] == "healthy"
        assert "subscription" in data
        assert data["subscription"]["is_subscribed"] is True
        assert data["subscription"]["active_subscriptions"] == 1
        assert data["subscription"]["total_events_received"] == 100
        assert "event_rate_per_minute" in data["subscription"]
        assert data["subscription"]["event_rate_per_minute"] > 0

    @pytest.mark.asyncio
    async def test_health_check_with_inactive_subscription(self):
        """Test health check with inactive subscription"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = True
        mock_manager.connection_attempts = 1
        mock_manager.successful_connections = 1
        mock_manager.failed_connections = 0

        mock_subscription = Mock()
        mock_subscription.is_subscribed = False

        def get_subscription_status():
            return {
                "is_subscribed": False,
                "active_subscriptions": 0,
                "total_events_received": 0,
                "events_by_type": {},
                "last_event_time": None
            }

        mock_subscription.get_subscription_status = get_subscription_status
        mock_manager.event_subscription = mock_subscription

        handler.set_connection_manager(mock_manager)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert data["status"] == "degraded"
        assert data["reason"] == "Not subscribed to events"

    @pytest.mark.asyncio
    async def test_health_check_with_no_events_received(self):
        """Test health check when no events received for extended period"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = True
        mock_manager.connection_attempts = 1
        mock_manager.successful_connections = 1
        mock_manager.failed_connections = 0

        mock_subscription = Mock()
        mock_subscription.is_subscribed = True
        mock_subscription.total_events_received = 0
        mock_subscription.subscription_start_time = datetime.now() - timedelta(seconds=120)

        def get_subscription_status():
            return {
                "is_subscribed": True,
                "active_subscriptions": 1,
                "total_events_received": 0,
                "events_by_type": {},
                "last_event_time": None
            }

        mock_subscription.get_subscription_status = get_subscription_status
        mock_manager.event_subscription = mock_subscription

        handler.set_connection_manager(mock_manager)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert data["status"] == "degraded"
        assert data["reason"] == "No events received in 60+ seconds"


class TestHealthCheckHandlerWithHistoricalCounter:
    """Test health check with historical event counter"""

    @pytest.mark.asyncio
    async def test_health_check_with_historical_counter(self):
        """Test health check includes historical event counts"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = True
        mock_manager.connection_attempts = 1
        mock_manager.successful_connections = 1
        mock_manager.failed_connections = 0

        mock_subscription = Mock()
        mock_subscription.is_subscribed = True

        def get_subscription_status():
            return {
                "is_subscribed": True,
                "active_subscriptions": 1,
                "total_events_received": 50,  # Current session
                "events_by_type": {"state_changed": 50},
                "last_event_time": datetime.now().isoformat(),
                "subscription_start_time": (datetime.now() - timedelta(minutes=1)).isoformat()
            }

        mock_subscription.get_subscription_status = get_subscription_status
        mock_manager.event_subscription = mock_subscription

        # Mock historical counter
        mock_counter = Mock()
        mock_counter.is_initialized = Mock(return_value=True)
        mock_counter.get_total_events_received = Mock(return_value=1000)  # Historical

        handler.set_connection_manager(mock_manager)
        handler.set_historical_counter(mock_counter)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert data["status"] == "healthy"
        assert data["subscription"]["session_events_received"] == 50
        assert data["subscription"]["historical_events_received"] == 1000
        assert data["subscription"]["total_events_received"] == 1050  # Combined

    @pytest.mark.asyncio
    async def test_health_check_with_uninitialized_historical_counter(self):
        """Test health check when historical counter is not initialized"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = True
        mock_manager.connection_attempts = 1
        mock_manager.successful_connections = 1
        mock_manager.failed_connections = 0

        mock_subscription = Mock()
        mock_subscription.is_subscribed = True

        def get_subscription_status():
            return {
                "is_subscribed": True,
                "active_subscriptions": 1,
                "total_events_received": 50,
                "events_by_type": {"state_changed": 50},
                "last_event_time": datetime.now().isoformat(),
                "subscription_start_time": (datetime.now() - timedelta(minutes=1)).isoformat()
            }

        mock_subscription.get_subscription_status = get_subscription_status
        mock_manager.event_subscription = mock_subscription

        # Mock uninitialized historical counter
        mock_counter = Mock()
        mock_counter.is_initialized = Mock(return_value=False)

        handler.set_connection_manager(mock_manager)
        handler.set_historical_counter(mock_counter)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert data["subscription"]["session_events_received"] == 50
        assert data["subscription"]["historical_events_received"] == 0
        assert data["subscription"]["total_events_received"] == 50


class TestHealthCheckHandlerErrorHandling:
    """Test health check error handling"""

    @pytest.mark.asyncio
    async def test_health_check_handles_exceptions(self):
        """Test health check handles exceptions gracefully"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = True

        # Make get_subscription_status raise an exception
        def raise_error():
            raise Exception("Test error")

        mock_subscription = Mock()
        mock_subscription.get_subscription_status = raise_error
        mock_manager.event_subscription = mock_subscription

        handler.set_connection_manager(mock_manager)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        # Should still return 200 but with unhealthy status
        assert response.status == 200
        assert data["status"] == "unhealthy"
        assert "error" in data

    @pytest.mark.asyncio
    async def test_health_check_always_returns_200(self):
        """Test that health check always returns 200 for load balancers"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = False  # Unhealthy

        handler.set_connection_manager(mock_manager)
        mock_request = Mock()

        response = await handler.handle(mock_request)

        # Should return 200 even when unhealthy
        assert response.status == 200


class TestHealthCheckHandlerEventRate:
    """Test event rate calculation"""

    @pytest.mark.asyncio
    async def test_event_rate_calculation(self):
        """Test event rate per minute calculation"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = True
        mock_manager.connection_attempts = 1
        mock_manager.successful_connections = 1
        mock_manager.failed_connections = 0

        # Simulate 100 events over 10 minutes = 10 events/min
        start_time = datetime.now() - timedelta(minutes=10)
        last_event_time = datetime.now()

        mock_subscription = Mock()
        mock_subscription.is_subscribed = True

        def get_subscription_status():
            return {
                "is_subscribed": True,
                "active_subscriptions": 1,
                "total_events_received": 100,
                "events_by_type": {"state_changed": 100},
                "last_event_time": last_event_time.isoformat(),
                "subscription_start_time": start_time.isoformat()
            }

        mock_subscription.get_subscription_status = get_subscription_status
        mock_manager.event_subscription = mock_subscription

        handler.set_connection_manager(mock_manager)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert "event_rate_per_minute" in data["subscription"]
        assert data["subscription"]["event_rate_per_minute"] > 0
        assert data["subscription"]["event_rate_per_minute"] <= 12  # ~10 events/min with some tolerance

    @pytest.mark.asyncio
    async def test_event_rate_with_no_events(self):
        """Test event rate when no events received"""
        handler = HealthCheckHandler()
        mock_manager = Mock()
        mock_manager.is_running = True
        mock_manager.connection_attempts = 1
        mock_manager.successful_connections = 1
        mock_manager.failed_connections = 0

        mock_subscription = Mock()
        mock_subscription.is_subscribed = True

        def get_subscription_status():
            return {
                "is_subscribed": True,
                "active_subscriptions": 1,
                "total_events_received": 0,
                "events_by_type": {},
                "last_event_time": None,
                "subscription_start_time": None
            }

        mock_subscription.get_subscription_status = get_subscription_status
        mock_manager.event_subscription = mock_subscription

        handler.set_connection_manager(mock_manager)
        mock_request = Mock()

        response = await handler.handle(mock_request)
        data = await response.json()

        assert data["subscription"]["event_rate_per_minute"] == 0
