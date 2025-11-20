"""
Tests for Discovery Service
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import WSMsgType
from src.discovery_service import DiscoveryService


class TestDiscoveryService:
    """Test cases for DiscoveryService class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = DiscoveryService()

    def test_initialization(self):
        """Test service initialization"""
        assert self.service.message_id_counter == 1000
        assert isinstance(self.service.pending_responses, dict)
        assert len(self.service.pending_responses) == 0

    def test_get_next_id(self):
        """Test message ID generation"""
        first_id = self.service._get_next_id()
        second_id = self.service._get_next_id()

        assert first_id == 1001
        assert second_id == 1002
        assert second_id > first_id

    @pytest.mark.asyncio
    async def test_discover_devices_success(self):
        """Test successful device discovery"""
        # Mock WebSocket
        mock_ws = AsyncMock()

        # Mock response
        mock_devices = [
            {
                "id": "device1",
                "name": "Living Room Light",
                "manufacturer": "Philips",
                "model": "Hue Bulb"
            },
            {
                "id": "device2",
                "name": "Bedroom Switch",
                "manufacturer": "Lutron",
                "model": "Caseta"
            }
        ]

        mock_response = MagicMock()
        mock_response.type = WSMsgType.TEXT
        mock_response.json.return_value = {
            "id": 1001,
            "type": "result",
            "success": True,
            "result": mock_devices
        }

        mock_ws.receive.return_value = mock_response

        # Test discover_devices
        devices = await self.service.discover_devices(mock_ws)

        # Assertions
        assert len(devices) == 2
        assert devices[0]["name"] == "Living Room Light"
        assert devices[1]["name"] == "Bedroom Switch"
        assert mock_ws.send_json.called

        # Check command sent
        call_args = mock_ws.send_json.call_args
        command = call_args[0][0]
        assert command["type"] == "config/device_registry/list"
        assert "id" in command

    @pytest.mark.asyncio
    async def test_discover_devices_empty_response(self):
        """Test device discovery with empty response"""
        mock_ws = AsyncMock()

        mock_response = MagicMock()
        mock_response.type = WSMsgType.TEXT
        mock_response.json.return_value = {
            "id": 1001,
            "type": "result",
            "success": True,
            "result": []
        }

        mock_ws.receive.return_value = mock_response

        devices = await self.service.discover_devices(mock_ws)

        assert len(devices) == 0
        assert isinstance(devices, list)

    @pytest.mark.asyncio
    async def test_discover_devices_failure(self):
        """Test device discovery failure"""
        mock_ws = AsyncMock()

        mock_response = MagicMock()
        mock_response.type = WSMsgType.TEXT
        mock_response.json.return_value = {
            "id": 1001,
            "type": "result",
            "success": False,
            "error": {"message": "Permission denied"}
        }

        mock_ws.receive.return_value = mock_response

        devices = await self.service.discover_devices(mock_ws)

        assert len(devices) == 0

    @pytest.mark.asyncio
    async def test_discover_devices_timeout(self):
        """Test device discovery timeout"""
        mock_ws = AsyncMock()
        mock_ws.receive.side_effect = asyncio.TimeoutError()

        devices = await self.service.discover_devices(mock_ws)

        assert len(devices) == 0

    @pytest.mark.asyncio
    async def test_discover_entities_success(self):
        """Test successful entity discovery"""
        mock_ws = AsyncMock()

        mock_entities = [
            {
                "entity_id": "light.living_room",
                "platform": "hue",
                "device_id": "device1"
            },
            {
                "entity_id": "switch.bedroom",
                "platform": "caseta",
                "device_id": "device2"
            }
        ]

        mock_response = MagicMock()
        mock_response.type = WSMsgType.TEXT
        mock_response.json.return_value = {
            "id": 1001,
            "type": "result",
            "success": True,
            "result": mock_entities
        }

        mock_ws.receive.return_value = mock_response

        entities = await self.service.discover_entities(mock_ws)

        assert len(entities) == 2
        assert entities[0]["entity_id"] == "light.living_room"
        assert entities[1]["entity_id"] == "switch.bedroom"

        # Check command sent
        call_args = mock_ws.send_json.call_args
        command = call_args[0][0]
        assert command["type"] == "config/entity_registry/list"

    @pytest.mark.asyncio
    async def test_discover_config_entries_success(self):
        """Test successful config entries discovery"""
        mock_ws = AsyncMock()

        mock_entries = [
            {
                "entry_id": "entry1",
                "title": "Philips Hue",
                "domain": "hue",
                "state": "loaded"
            },
            {
                "entry_id": "entry2",
                "title": "Google Nest",
                "domain": "nest",
                "state": "loaded"
            }
        ]

        mock_response = MagicMock()
        mock_response.type = WSMsgType.TEXT
        mock_response.json.return_value = {
            "id": 1001,
            "type": "result",
            "success": True,
            "result": mock_entries
        }

        mock_ws.receive.return_value = mock_response

        entries = await self.service.discover_config_entries(mock_ws)

        assert len(entries) == 2
        assert entries[0]["title"] == "Philips Hue"
        assert entries[1]["domain"] == "nest"

        # Check command sent
        call_args = mock_ws.send_json.call_args
        command = call_args[0][0]
        assert command["type"] == "config_entries/list"

    @pytest.mark.asyncio
    async def test_discover_all_success(self):
        """Test complete discovery of all registries"""
        mock_ws = AsyncMock()

        # Setup mock responses for all three commands
        responses = [
            # Devices response
            MagicMock(
                type=WSMsgType.TEXT,
                json=lambda: {
                    "id": 1001,
                    "type": "result",
                    "success": True,
                    "result": [{"id": "dev1", "name": "Device 1"}]
                }
            ),
            # Entities response
            MagicMock(
                type=WSMsgType.TEXT,
                json=lambda: {
                    "id": 1002,
                    "type": "result",
                    "success": True,
                    "result": [{"entity_id": "light.test"}]
                }
            ),
            # Config entries response
            MagicMock(
                type=WSMsgType.TEXT,
                json=lambda: {
                    "id": 1003,
                    "type": "result",
                    "success": True,
                    "result": [{"entry_id": "entry1", "title": "Test"}]
                }
            )
        ]

        mock_ws.receive.side_effect = responses

        result = await self.service.discover_all(mock_ws)

        assert "devices" in result
        assert "entities" in result
        assert "config_entries" in result
        assert len(result["devices"]) == 1
        assert len(result["entities"]) == 1
        assert len(result["config_entries"]) == 1

    @pytest.mark.asyncio
    async def test_discover_all_partial_failure(self):
        """Test discovery with partial failures"""
        mock_ws = AsyncMock()

        # First command succeeds, others timeout
        responses = [
            MagicMock(
                type=WSMsgType.TEXT,
                json=lambda: {
                    "id": 1001,
                    "type": "result",
                    "success": True,
                    "result": [{"id": "dev1"}]
                }
            )
        ]

        mock_ws.receive.side_effect = responses + [asyncio.TimeoutError()] * 2

        result = await self.service.discover_all(mock_ws)

        # Should still return results even with partial failures
        assert "devices" in result
        assert "entities" in result
        assert "config_entries" in result
        assert len(result["devices"]) == 1
        assert len(result["entities"]) == 0  # Failed
        assert len(result["config_entries"]) == 0  # Failed

    @pytest.mark.asyncio
    async def test_wait_for_response_success(self):
        """Test waiting for response with correct message ID"""
        mock_ws = AsyncMock()

        expected_response = {
            "id": 100,
            "type": "result",
            "success": True,
            "result": []
        }

        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.TEXT
        mock_msg.json.return_value = expected_response

        mock_ws.receive.return_value = mock_msg

        response = await self.service._wait_for_response(mock_ws, 100, timeout=1.0)

        assert response == expected_response

    @pytest.mark.asyncio
    async def test_wait_for_response_timeout(self):
        """Test waiting for response with timeout"""
        mock_ws = AsyncMock()
        mock_ws.receive.side_effect = asyncio.TimeoutError()

        with pytest.raises(asyncio.TimeoutError):
            await self.service._wait_for_response(mock_ws, 100, timeout=0.1)

    @pytest.mark.asyncio
    async def test_wait_for_response_wrong_id(self):
        """Test waiting for response when wrong message ID received first"""
        mock_ws = AsyncMock()

        # First message has wrong ID, second has correct ID
        wrong_msg = MagicMock()
        wrong_msg.type = WSMsgType.TEXT
        wrong_msg.json.return_value = {"id": 99, "type": "result"}

        correct_msg = MagicMock()
        correct_msg.type = WSMsgType.TEXT
        correct_msg.json.return_value = {"id": 100, "type": "result", "success": True}

        mock_ws.receive.side_effect = [wrong_msg, correct_msg]

        response = await self.service._wait_for_response(mock_ws, 100, timeout=2.0)

        assert response["id"] == 100
        assert response["success"] is True

    @pytest.mark.asyncio
    async def test_subscribe_to_device_registry_events_success(self):
        """Test subscribing to device registry events"""
        mock_ws = AsyncMock()

        mock_response = MagicMock()
        mock_response.type = WSMsgType.TEXT
        mock_response.json.return_value = {
            "id": 1001,
            "type": "result",
            "success": True,
            "result": None
        }

        mock_ws.receive.return_value = mock_response

        result = await self.service.subscribe_to_device_registry_events(mock_ws)

        assert result is True
        assert mock_ws.send_json.called

        # Verify subscription command
        call_args = mock_ws.send_json.call_args
        command = call_args[0][0]
        assert command["type"] == "subscribe_events"
        assert command["event_type"] == "device_registry_updated"

    @pytest.mark.asyncio
    async def test_subscribe_to_entity_registry_events_success(self):
        """Test subscribing to entity registry events"""
        mock_ws = AsyncMock()

        mock_response = MagicMock()
        mock_response.type = WSMsgType.TEXT
        mock_response.json.return_value = {
            "id": 1001,
            "type": "result",
            "success": True,
            "result": None
        }

        mock_ws.receive.return_value = mock_response

        result = await self.service.subscribe_to_entity_registry_events(mock_ws)

        assert result is True

        # Verify subscription command
        call_args = mock_ws.send_json.call_args
        command = call_args[0][0]
        assert command["type"] == "subscribe_events"
        assert command["event_type"] == "entity_registry_updated"

    @pytest.mark.asyncio
    async def test_handle_device_registry_event(self):
        """Test handling device registry update event"""
        event = {
            "event_type": "device_registry_updated",
            "data": {
                "action": "create",
                "device_id": "dev123",
                "device": {
                    "id": "dev123",
                    "name": "New Device",
                    "manufacturer": "Acme",
                    "model": "X1"
                }
            }
        }

        result = await self.service.handle_device_registry_event(event)

        assert result is True

    @pytest.mark.asyncio
    async def test_handle_device_registry_event_no_data(self):
        """Test handling device registry event with no device data"""
        event = {
            "event_type": "device_registry_updated",
            "data": {
                "action": "remove",
                "device_id": "dev123"
            }
        }

        result = await self.service.handle_device_registry_event(event)

        assert result is True

    @pytest.mark.asyncio
    async def test_handle_entity_registry_event(self):
        """Test handling entity registry update event"""
        event = {
            "event_type": "entity_registry_updated",
            "data": {
                "action": "create",
                "entity_id": "light.new_light",
                "entity": {
                    "entity_id": "light.new_light",
                    "platform": "hue",
                    "device_id": "dev123"
                }
            }
        }

        result = await self.service.handle_entity_registry_event(event)

        assert result is True

    @pytest.mark.asyncio
    async def test_handle_entity_registry_event_malformed(self):
        """Test handling malformed entity registry event"""
        event = {
            "event_type": "entity_registry_updated",
            "data": {}
        }

        result = await self.service.handle_entity_registry_event(event)

        # Should handle gracefully
        assert result is True

