"""
Event Generator for HA Simulator

Generates realistic Home Assistant events based on analyzed patterns.
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Any

from aiohttp.web_ws import WebSocketResponse

logger = logging.getLogger(__name__)

class EventGenerator:
    """Generates realistic HA events for simulation"""

    def __init__(self, config: dict[str, Any], patterns: dict[str, Any]):
        self.config = config
        self.patterns = patterns
        self.entity_states: dict[str, dict[str, Any]] = {}
        self.generation_tasks: dict[str, asyncio.Task] = {}
        self.running = False
        self.clients: list[WebSocketResponse] = []
        self.event_counter = 0

    async def start_generation(self, clients: list[WebSocketResponse]):
        """Start event generation for all entities"""
        self.running = True
        self.clients = clients

        # Initialize entity states
        for entity_id, entity_config in self.patterns["entities"].items():
            self._initialize_entity_state(entity_id, entity_config)

        # Start generation tasks
        for entity_id, entity_config in self.patterns["entities"].items():
            task = asyncio.create_task(
                self._generate_entity_events(entity_id, entity_config),
            )
            self.generation_tasks[entity_id] = task

        logger.info(f"Started event generation for {len(self.generation_tasks)} entities")

    async def stop_generation(self):
        """Stop all event generation"""
        self.running = False

        for task in self.generation_tasks.values():
            task.cancel()

        await asyncio.gather(*self.generation_tasks.values(), return_exceptions=True)
        self.generation_tasks.clear()

        logger.info("Stopped event generation")

    def _initialize_entity_state(self, entity_id: str, entity_config: dict[str, Any]):
        """Initialize entity state"""
        self.entity_states[entity_id] = {
            "state": self._generate_initial_value(entity_config),
            "last_updated": datetime.now(timezone.utc),
            "attributes": self._generate_attributes(entity_config),
        }

    def _generate_initial_value(self, entity_config: dict[str, Any]) -> str:
        """Generate initial value for entity"""
        base_value = entity_config.get("base_value", 0)
        variance = entity_config.get("variance")

        if variance is None:
            return str(base_value)

        if isinstance(base_value, (int, float)):
            value = base_value + random.uniform(-variance, variance)
            return f"{value:.1f}"
        return str(base_value)

    def _generate_attributes(self, entity_config: dict[str, Any]) -> dict[str, Any]:
        """Generate entity attributes"""
        attributes = {
            "friendly_name": entity_config.get("friendly_name", entity_config["entity_id"]),
            "device_class": entity_config.get("device_class"),
            "unit_of_measurement": entity_config.get("unit_of_measurement"),
        }

        # Remove None values
        return {k: v for k, v in attributes.items() if v is not None}

    async def _generate_entity_events(self, entity_id: str, entity_config: dict[str, Any]):
        """Generate events for a specific entity"""
        update_interval = entity_config.get("update_interval", 30)

        logger.info(f"Starting event generation for {entity_id} (interval: {update_interval}s)")

        while self.running:
            try:
                await asyncio.sleep(update_interval)

                if not self.running:
                    break

                # Generate new state
                new_state = self._generate_new_state(entity_id, entity_config)
                old_state = self.entity_states[entity_id]["state"]

                # Always send event for demonstration (in real HA, only on state change)
                await self._send_state_changed_event(entity_id, old_state, new_state)
                self.entity_states[entity_id]["state"] = new_state
                self.entity_states[entity_id]["last_updated"] = datetime.now(timezone.utc)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error generating events for {entity_id}: {e}")

    def _generate_new_state(self, entity_id: str, entity_config: dict[str, Any]) -> str:
        """Generate new state value"""
        current_state = self.entity_states[entity_id]["state"]
        base_value = entity_config.get("base_value", 0)
        variance = entity_config.get("variance")

        if variance is None:
            return str(base_value)

        if isinstance(base_value, (int, float)):
            try:
                current_numeric = float(current_state)
                # Add small random change
                change = random.uniform(-variance * 0.1, variance * 0.1)
                new_value = current_numeric + change
                return f"{new_value:.1f}"
            except ValueError:
                return self._generate_initial_value(entity_config)
        else:
            return str(base_value)

    async def _send_state_changed_event(self, entity_id: str, old_state: str, new_state: str):
        """Send state_changed event to all clients"""
        event = self._create_state_changed_event(entity_id, old_state, new_state)

        if not event:
            return

        self.event_counter += 1

        # Broadcast to all clients
        disconnected_clients = []

        for client in self.clients:
            try:
                await client.send_str(json.dumps(event))
            except Exception as e:
                logger.exception(f"Error sending event to client: {e}")
                disconnected_clients.append(client)

        # Remove disconnected clients
        for client in disconnected_clients:
            if client in self.clients:
                self.clients.remove(client)

        logger.debug(f"Sent event #{self.event_counter} for {entity_id}: {old_state} -> {new_state}")

    def _create_state_changed_event(self, entity_id: str, old_state: str, new_state: str) -> dict[str, Any] | None:
        """Create state_changed event"""
        now = datetime.now(timezone.utc)
        entity_config = self.patterns["entities"].get(entity_id)

        if not entity_config:
            return None

        return {
            "type": "event",
            "event": {
                "event_type": "state_changed",
                "time_fired": now.isoformat(),
                "origin": "LOCAL",
                "context": {
                    "id": f"sim_{int(now.timestamp() * 1000)}",
                    "parent_id": None,
                    "user_id": None,
                },
                "data": {
                    "entity_id": entity_id,
                    "old_state": {
                        "entity_id": entity_id,
                        "state": old_state,
                        "attributes": self.entity_states[entity_id]["attributes"],
                        "last_changed": self.entity_states[entity_id]["last_updated"].isoformat(),
                        "last_updated": self.entity_states[entity_id]["last_updated"].isoformat(),
                    },
                    "new_state": {
                        "entity_id": entity_id,
                        "state": new_state,
                        "attributes": self.entity_states[entity_id]["attributes"],
                        "last_changed": now.isoformat(),
                        "last_updated": now.isoformat(),
                    },
                },
            },
        }

    def get_stats(self) -> dict[str, Any]:
        """Get event generation statistics"""
        return {
            "running": self.running,
            "entities": len(self.entity_states),
            "active_tasks": len(self.generation_tasks),
            "events_generated": self.event_counter,
            "clients": len(self.clients),
        }

