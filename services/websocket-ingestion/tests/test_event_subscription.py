"""
Tests for Event Subscription Manager
"""

from unittest.mock import AsyncMock

import pytest
from src.event_subscription import EventSubscriptionManager


class TestEventSubscriptionManager:
    """Test cases for EventSubscriptionManager class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.subscription_manager = EventSubscriptionManager()

    def test_initialization(self):
        """Test subscription manager initialization"""
        assert self.subscription_manager.subscriptions == {}
        assert self.subscription_manager.subscription_counter == 1
        assert self.subscription_manager.is_subscribed is False
        assert self.subscription_manager.total_events_received == 0
        assert self.subscription_manager.events_by_type == {}

    @pytest.mark.asyncio
    async def test_subscribe_to_single_event_type(self):
        """Test subscribing to a single event type"""
        mock_client = AsyncMock()
        mock_client.send_message.return_value = True

        result = await self.subscription_manager.subscribe_to_events(mock_client, ["state_changed"])

        assert result is True
        assert self.subscription_manager.is_subscribed is True
        assert len(self.subscription_manager.subscriptions) == 1
        mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_to_multiple_event_types(self):
        """Test subscribing to multiple event types"""
        mock_client = AsyncMock()
        mock_client.send_message.return_value = True

        result = await self.subscription_manager.subscribe_to_events(
            mock_client,
            ["state_changed", "call_service"],
        )

        assert result is True
        assert self.subscription_manager.is_subscribed is True
        assert len(self.subscription_manager.subscriptions) == 2
        assert mock_client.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_subscribe_failure(self):
        """Test subscription failure"""
        mock_client = AsyncMock()
        mock_client.send_message.return_value = False

        result = await self.subscription_manager.subscribe_to_events(mock_client, ["state_changed"])

        assert result is False
        assert self.subscription_manager.is_subscribed is False

    @pytest.mark.asyncio
    async def test_handle_subscription_result_success(self):
        """Test handling successful subscription result"""
        message = {
            "type": "result",
            "id": 1,
            "success": True,
        }

        # Set up a pending subscription
        self.subscription_manager.subscriptions[1] = {
            "event_type": "state_changed",
            "subscribed_at": "2024-01-01T00:00:00",
            "status": "pending",
        }

        result = await self.subscription_manager.handle_subscription_result(message)

        assert result is True
        assert self.subscription_manager.subscriptions[1]["status"] == "active"

    @pytest.mark.asyncio
    async def test_handle_subscription_result_failure(self):
        """Test handling failed subscription result"""
        message = {
            "type": "result",
            "id": 1,
            "success": False,
            "error": {"message": "Invalid event type"},
        }

        # Set up a pending subscription
        self.subscription_manager.subscriptions[1] = {
            "event_type": "invalid_type",
            "subscribed_at": "2024-01-01T00:00:00",
            "status": "pending",
        }

        result = await self.subscription_manager.handle_subscription_result(message)

        assert result is False
        assert self.subscription_manager.subscriptions[1]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_handle_event_message(self):
        """Test handling incoming event message"""
        message = {
            "type": "event",
            "event": {
                "event_type": "state_changed",
                "old_state": {"state": "off"},
                "new_state": {"state": "on", "entity_id": "light.living_room"},
            },
        }

        result = await self.subscription_manager.handle_event_message(message)

        assert result is True
        assert self.subscription_manager.total_events_received == 1
        assert self.subscription_manager.events_by_type["state_changed"] == 1

    @pytest.mark.asyncio
    async def test_handle_event_message_with_handler(self):
        """Test handling event message with registered handler"""
        message = {
            "type": "event",
            "event": {
                "event_type": "state_changed",
                "old_state": {"state": "off"},
                "new_state": {"state": "on", "entity_id": "light.living_room"},
            },
        }

        # Register a handler
        handler_called = False
        async def test_handler(event_data):
            nonlocal handler_called
            handler_called = True

        self.subscription_manager.register_event_handler("state_changed", test_handler)

        result = await self.subscription_manager.handle_event_message(message)

        assert result is True
        assert handler_called is True

    @pytest.mark.asyncio
    async def test_handle_non_event_message(self):
        """Test handling non-event message"""
        message = {
            "type": "ping",
            "data": "pong",
        }

        result = await self.subscription_manager.handle_event_message(message)

        assert result is True
        assert self.subscription_manager.total_events_received == 0

    def test_extract_event_summary_state_changed(self):
        """Test extracting summary from state_changed event"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off"},
            "new_state": {"state": "on", "entity_id": "light.living_room"},
        }

        summary = self.subscription_manager._extract_event_summary(event_data)

        assert "light.living_room" in summary
        assert "off -> on" in summary

    def test_extract_event_summary_other_event(self):
        """Test extracting summary from other event types"""
        event_data = {
            "event_type": "call_service",
            "domain": "light",
            "service": "turn_on",
        }

        summary = self.subscription_manager._extract_event_summary(event_data)

        assert "call_service" in summary

    def test_register_event_handler(self):
        """Test registering event handler"""
        async def test_handler(event_data):
            pass

        self.subscription_manager.register_event_handler("state_changed", test_handler)

        assert "state_changed" in self.subscription_manager.subscription_handlers

    @pytest.mark.asyncio
    async def test_resubscribe_after_reconnection(self):
        """Test resubscribing after reconnection"""
        mock_client = AsyncMock()
        mock_client.send_message.return_value = True

        # Set up previous subscriptions
        self.subscription_manager.subscriptions[1] = {
            "event_type": "state_changed",
            "subscribed_at": "2024-01-01T00:00:00",
            "status": "active",
        }
        self.subscription_manager.is_subscribed = True

        result = await self.subscription_manager.resubscribe_after_reconnection(mock_client)

        assert result is True
        assert self.subscription_manager.is_subscribed is True
        mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_resubscribe_no_previous_subscriptions(self):
        """Test resubscribing with no previous subscriptions"""
        mock_client = AsyncMock()

        result = await self.subscription_manager.resubscribe_after_reconnection(mock_client)

        assert result is True
        mock_client.send_message.assert_not_called()

    def test_get_subscription_status(self):
        """Test getting subscription status"""
        # Set up some subscriptions
        self.subscription_manager.subscriptions[1] = {
            "event_type": "state_changed",
            "subscribed_at": "2024-01-01T00:00:00",
            "status": "active",
        }
        self.subscription_manager.subscriptions[2] = {
            "event_type": "call_service",
            "subscribed_at": "2024-01-01T00:00:00",
            "status": "pending",
        }
        self.subscription_manager.is_subscribed = True
        self.subscription_manager.total_events_received = 5
        self.subscription_manager.events_by_type = {"state_changed": 3, "call_service": 2}

        status = self.subscription_manager.get_subscription_status()

        assert status["is_subscribed"] is True
        assert status["total_subscriptions"] == 2
        assert status["active_subscriptions"] == 1
        assert status["pending_subscriptions"] == 1
        assert status["failed_subscriptions"] == 0
        assert status["total_events_received"] == 5
        assert status["events_by_type"]["state_changed"] == 3

    def test_reset_statistics(self):
        """Test resetting statistics"""
        # Set up some data
        self.subscription_manager.total_events_received = 10
        self.subscription_manager.events_by_type = {"state_changed": 5}
        self.subscription_manager.last_event_time = "2024-01-01T00:00:00"

        self.subscription_manager.reset_statistics()

        assert self.subscription_manager.total_events_received == 0
        assert self.subscription_manager.events_by_type == {}
        assert self.subscription_manager.last_event_time is None
