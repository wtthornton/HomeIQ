"""
Function Registry

Registry of callable HA functions for immediate action execution.
Maps natural language actions to HA service calls.

Created: Phase 4 - Function Calling & Device Context
"""

import logging
from collections.abc import Callable
from typing import Any

from ...clients.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


class FunctionRegistry:
    """
    Registry of callable Home Assistant functions.
    
    Maps function names to HA service calls for immediate action execution.
    """

    def __init__(self, ha_client: HomeAssistantClient):
        """
        Initialize function registry.
        
        Args:
            ha_client: Home Assistant client for service calls
        """
        self.ha_client = ha_client
        self.functions = self._register_functions()

        logger.info(f"FunctionRegistry initialized with {len(self.functions)} functions")

    def _register_functions(self) -> dict[str, Callable]:
        """Register all available functions"""
        return {
            "turn_on_light": self._turn_on_light,
            "turn_off_light": self._turn_off_light,
            "set_light_brightness": self._set_light_brightness,
            "turn_on_switch": self._turn_on_switch,
            "turn_off_switch": self._turn_off_switch,
            "get_entity_state": self._get_entity_state,
            "set_temperature": self._set_temperature,
            "lock_door": self._lock_door,
            "unlock_door": self._unlock_door,
        }

    async def call_function(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute function by name.
        
        Args:
            name: Function name
            params: Function parameters
        
        Returns:
            Function result dictionary
        """
        if name not in self.functions:
            raise ValueError(f"Unknown function: {name}")

        try:
            func = self.functions[name]
            result = await func(params)
            return {
                "success": True,
                "result": result,
                "function_name": name
            }
        except Exception as e:
            logger.error(f"Function call failed: {name} - {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "function_name": name
            }

    async def _turn_on_light(self, params: dict[str, Any]) -> dict[str, Any]:
        """Turn on a light"""
        entity_id = params.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id required")

        await self.ha_client.call_service(
            domain="light",
            service="turn_on",
            entity_id=entity_id,
            service_data=params.get("service_data", {})
        )

        return {"entity_id": entity_id, "action": "turned_on"}

    async def _turn_off_light(self, params: dict[str, Any]) -> dict[str, Any]:
        """Turn off a light"""
        entity_id = params.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id required")

        await self.ha_client.call_service(
            domain="light",
            service="turn_off",
            entity_id=entity_id
        )

        return {"entity_id": entity_id, "action": "turned_off"}

    async def _set_light_brightness(self, params: dict[str, Any]) -> dict[str, Any]:
        """Set light brightness"""
        entity_id = params.get("entity_id")
        brightness = params.get("brightness")

        if not entity_id or brightness is None:
            raise ValueError("entity_id and brightness required")

        await self.ha_client.call_service(
            domain="light",
            service="turn_on",
            entity_id=entity_id,
            service_data={"brightness": brightness}
        )

        return {"entity_id": entity_id, "brightness": brightness}

    async def _turn_on_switch(self, params: dict[str, Any]) -> dict[str, Any]:
        """Turn on a switch"""
        entity_id = params.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id required")

        await self.ha_client.call_service(
            domain="switch",
            service="turn_on",
            entity_id=entity_id
        )

        return {"entity_id": entity_id, "action": "turned_on"}

    async def _turn_off_switch(self, params: dict[str, Any]) -> dict[str, Any]:
        """Turn off a switch"""
        entity_id = params.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id required")

        await self.ha_client.call_service(
            domain="switch",
            service="turn_off",
            entity_id=entity_id
        )

        return {"entity_id": entity_id, "action": "turned_off"}

    async def _get_entity_state(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get entity state"""
        entity_id = params.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id required")

        state = await self.ha_client.get_entity_state(entity_id)
        return {"entity_id": entity_id, "state": state}

    async def _set_temperature(self, params: dict[str, Any]) -> dict[str, Any]:
        """Set thermostat temperature"""
        entity_id = params.get("entity_id")
        temperature = params.get("temperature")

        if not entity_id or temperature is None:
            raise ValueError("entity_id and temperature required")

        await self.ha_client.call_service(
            domain="climate",
            service="set_temperature",
            entity_id=entity_id,
            service_data={"temperature": temperature}
        )

        return {"entity_id": entity_id, "temperature": temperature}

    async def _lock_door(self, params: dict[str, Any]) -> dict[str, Any]:
        """Lock a door"""
        entity_id = params.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id required")

        await self.ha_client.call_service(
            domain="lock",
            service="lock",
            entity_id=entity_id
        )

        return {"entity_id": entity_id, "action": "locked"}

    async def _unlock_door(self, params: dict[str, Any]) -> dict[str, Any]:
        """Unlock a door"""
        entity_id = params.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id required")

        await self.ha_client.call_service(
            domain="lock",
            service="unlock",
            entity_id=entity_id
        )

        return {"entity_id": entity_id, "action": "unlocked"}

