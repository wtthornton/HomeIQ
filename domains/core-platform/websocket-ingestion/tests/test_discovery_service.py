"""
Tests for Discovery Service

Discovery uses the message-routing pattern: a command goes out over the
WebSocket, a Future is registered in ``pending_responses``, and the connection
manager's listen loop resolves it via ``handle_message_result``. The
``FakeHomeAssistant`` harness below stands in for that listen loop so tests
exercise the real routing path rather than reading the socket directly.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from src.discovery_service import DiscoveryService


class FakeHomeAssistant:
    """Canned-response WebSocket that replies through discovery's message routing."""

    def __init__(self, service: DiscoveryService):
        self.service = service
        self.commands: list[dict] = []
        self._replies: dict[str, dict] = {}
        self._tasks: list[asyncio.Task] = []
        self.websocket = AsyncMock()
        self.websocket.send_json = self._send_json

    def on(self, command_type: str, *, result=None, success: bool = True, error=None):
        """Register the reply for a command type. Unregistered types get no reply."""
        self._replies[command_type] = {"result": result, "success": success, "error": error}
        return self

    async def _send_json(self, command: dict):
        self.commands.append(command)
        reply = self._replies.get(command["type"])
        if reply is not None:
            self._tasks.append(asyncio.create_task(self._respond(command["id"], reply)))

    async def _respond(self, message_id: int, reply: dict):
        # _wait_for_response registers its Future only after send_json returns,
        # so yield until the pending entry appears before resolving it.
        for _ in range(100):
            if message_id in self.service.pending_responses:
                break
            await asyncio.sleep(0)

        payload = {"id": message_id, "type": "result", "success": reply["success"]}
        if reply["success"]:
            payload["result"] = reply["result"]
        else:
            payload["error"] = reply["error"] or {"message": "Unknown error"}
        self.service.handle_message_result(payload)

    def command_of(self, command_type: str) -> dict:
        """Return the first command of the given type that was sent."""
        return next(c for c in self.commands if c["type"] == command_type)


class TestDiscoveryService:
    """Test cases for DiscoveryService class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = DiscoveryService()

    @pytest.fixture(autouse=True)
    def _block_http_fallbacks(self, monkeypatch):
        """Keep the HTTP fallbacks off the network regardless of ambient HA_TOKEN."""
        monkeypatch.setattr(self.service, "_discover_devices_http", AsyncMock(return_value=[]))
        monkeypatch.setattr(self.service, "_discover_entities_http", AsyncMock(return_value=[]))
        monkeypatch.setattr(self.service, "discover_services", AsyncMock(return_value={}))
        monkeypatch.setattr(self.service, "store_discovery_results", AsyncMock(return_value=None))

    def test_initialization(self):
        """Test service initialization"""
        assert self.service.message_id_manager is not None
        assert isinstance(self.service.pending_responses, dict)
        assert len(self.service.pending_responses) == 0

    @pytest.mark.asyncio
    async def test_get_next_id_strictly_increasing(self):
        """Message IDs come from the shared manager and must strictly increase"""
        first_id = await self.service._get_next_id()
        second_id = await self.service._get_next_id()

        assert second_id > first_id

    @pytest.mark.asyncio
    async def test_discover_devices_success(self):
        """Test successful device discovery"""
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
        ha = FakeHomeAssistant(self.service).on(
            "config/device_registry/list", result=mock_devices
        )

        devices = await self.service.discover_devices(ha.websocket)

        assert len(devices) == 2
        assert devices[0]["name"] == "Living Room Light"
        assert devices[1]["name"] == "Bedroom Switch"

        command = ha.command_of("config/device_registry/list")
        assert "id" in command

        # Routing state is cleaned up once the response lands
        assert self.service.pending_responses == {}

    @pytest.mark.asyncio
    async def test_discover_devices_caches_metadata(self):
        """Device discovery populates the area and metadata caches (Epic 23.2/23.5)"""
        ha = FakeHomeAssistant(self.service).on(
            "config/device_registry/list",
            result=[{
                "id": "device1",
                "name": "Living Room Light",
                "area_id": "living_room",
                "manufacturer": "Philips",
                "model": "Hue Bulb",
                "sw_version": "1.2.3",
            }],
        )

        await self.service.discover_devices(ha.websocket)

        assert self.service.device_to_area["device1"] == "living_room"
        assert self.service.device_metadata["device1"]["manufacturer"] == "Philips"
        assert self.service.device_metadata["device1"]["sw_version"] == "1.2.3"

    @pytest.mark.asyncio
    async def test_discover_devices_empty_response(self):
        """Test device discovery with empty response"""
        ha = FakeHomeAssistant(self.service).on("config/device_registry/list", result=[])

        devices = await self.service.discover_devices(ha.websocket)

        assert devices == []

    @pytest.mark.asyncio
    async def test_discover_devices_failure(self):
        """Test device discovery failure"""
        ha = FakeHomeAssistant(self.service).on(
            "config/device_registry/list",
            success=False,
            error={"message": "Permission denied"},
        )

        devices = await self.service.discover_devices(ha.websocket)

        assert devices == []

    @pytest.mark.asyncio
    async def test_discover_devices_no_response_falls_back(self, monkeypatch):
        """A timed-out response yields an empty list rather than raising"""
        monkeypatch.setattr(self.service, "_wait_for_response", AsyncMock(return_value=None))
        ha = FakeHomeAssistant(self.service)

        devices = await self.service.discover_devices(ha.websocket)

        assert devices == []
        self.service._discover_devices_http.assert_awaited()

    @pytest.mark.asyncio
    async def test_discover_devices_without_transport(self):
        """No websocket and no connection manager means nothing to send on"""
        devices = await self.service.discover_devices()

        assert devices == []

    @pytest.mark.asyncio
    async def test_discover_entities_success(self):
        """Test successful entity discovery"""
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
        ha = FakeHomeAssistant(self.service).on(
            "config/entity_registry/list", result=mock_entities
        )

        entities = await self.service.discover_entities(ha.websocket)

        assert len(entities) == 2
        assert entities[0]["entity_id"] == "light.living_room"
        assert entities[1]["entity_id"] == "switch.bedroom"
        assert ha.command_of("config/entity_registry/list")["type"] == "config/entity_registry/list"

    @pytest.mark.asyncio
    async def test_discover_config_entries_success(self):
        """Test successful config entries discovery"""
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
        ha = FakeHomeAssistant(self.service).on("config_entries/list", result=mock_entries)

        entries = await self.service.discover_config_entries(ha.websocket)

        assert len(entries) == 2
        assert entries[0]["title"] == "Philips Hue"
        assert entries[1]["domain"] == "nest"
        assert ha.command_of("config_entries/list")["type"] == "config_entries/list"

    @pytest.mark.asyncio
    async def test_discover_config_entries_failure(self):
        """A failed config entries command returns an empty list"""
        ha = FakeHomeAssistant(self.service).on(
            "config_entries/list", success=False, error={"message": "nope"}
        )

        entries = await self.service.discover_config_entries(ha.websocket)

        assert entries == []

    @pytest.mark.asyncio
    async def test_discover_all_success(self):
        """Test complete discovery of all registries"""
        ha = (
            FakeHomeAssistant(self.service)
            .on("config/device_registry/list", result=[{"id": "dev1", "name": "Device 1"}])
            .on("config/entity_registry/list", result=[{"entity_id": "light.test"}])
            .on("config_entries/list", result=[{"entry_id": "entry1", "title": "Test"}])
        )

        result = await self.service.discover_all(ha.websocket, store=False)

        assert len(result["devices"]) == 1
        assert len(result["entities"]) == 1
        assert len(result["config_entries"]) == 1
        assert "services" in result
        self.service.store_discovery_results.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_discover_all_stores_when_requested(self):
        """discover_all persists results when store=True"""
        ha = (
            FakeHomeAssistant(self.service)
            .on("config/device_registry/list", result=[{"id": "dev1"}])
            .on("config/entity_registry/list", result=[{"entity_id": "light.test"}])
            .on("config_entries/list", result=[])
        )

        await self.service.discover_all(ha.websocket, store=True)

        self.service.store_discovery_results.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_discover_all_partial_failure(self):
        """Test discovery with partial failures"""
        ha = (
            FakeHomeAssistant(self.service)
            .on("config/device_registry/list", result=[{"id": "dev1"}])
            .on("config/entity_registry/list", success=False, error={"message": "boom"})
            .on("config_entries/list", success=False, error={"message": "boom"})
        )

        result = await self.service.discover_all(ha.websocket, store=False)

        # Should still return results even with partial failures
        assert len(result["devices"]) == 1
        assert result["entities"] == []
        assert result["config_entries"] == []

    @pytest.mark.asyncio
    async def test_wait_for_response_success(self):
        """Test waiting for a response routed in by the listen loop"""
        expected_response = {
            "id": 100,
            "type": "result",
            "success": True,
            "result": []
        }

        async def deliver():
            while 100 not in self.service.pending_responses:
                await asyncio.sleep(0)
            self.service.handle_message_result(expected_response)

        asyncio.create_task(deliver())

        response = await self.service._wait_for_response(None, 100, timeout=1.0)

        assert response == expected_response
        assert self.service.pending_responses == {}

    @pytest.mark.asyncio
    async def test_wait_for_response_timeout(self):
        """Timing out returns None rather than raising"""
        response = await self.service._wait_for_response(None, 100, timeout=0.05)

        assert response is None

    @pytest.mark.asyncio
    async def test_wait_for_response_wrong_id(self):
        """A message for a different ID must not resolve this request"""

        async def deliver():
            while 100 not in self.service.pending_responses:
                await asyncio.sleep(0)
            # Wrong ID is not routed anywhere
            assert self.service.handle_message_result({"id": 99, "type": "result"}) is False
            self.service.handle_message_result(
                {"id": 100, "type": "result", "success": True}
            )

        asyncio.create_task(deliver())

        response = await self.service._wait_for_response(None, 100, timeout=2.0)

        assert response["id"] == 100
        assert response["success"] is True

    def test_handle_message_result_ignores_non_result_messages(self):
        """Only `result` messages are routed to pending discovery requests"""
        assert self.service.handle_message_result(
            {"id": 1, "type": "event", "event": {}}
        ) is False

    @pytest.mark.asyncio
    async def test_subscribe_to_device_registry_events_success(self):
        """Test subscribing to device registry events"""
        ha = FakeHomeAssistant(self.service).on("subscribe_events", result=None)

        result = await self.service.subscribe_to_device_registry_events(ha.websocket)

        assert result is True
        command = ha.command_of("subscribe_events")
        assert command["event_type"] == "device_registry_updated"

    @pytest.mark.asyncio
    async def test_subscribe_to_entity_registry_events_success(self):
        """Test subscribing to entity registry events"""
        ha = FakeHomeAssistant(self.service).on("subscribe_events", result=None)

        result = await self.service.subscribe_to_entity_registry_events(ha.websocket)

        assert result is True
        command = ha.command_of("subscribe_events")
        assert command["event_type"] == "entity_registry_updated"

    @pytest.mark.asyncio
    async def test_subscribe_to_device_registry_events_failure(self):
        """A rejected subscription reports failure"""
        ha = FakeHomeAssistant(self.service).on(
            "subscribe_events", success=False, error={"message": "denied"}
        )

        result = await self.service.subscribe_to_device_registry_events(ha.websocket)

        assert result is False

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
