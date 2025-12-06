"""
Home Assistant API Client for HA AI Agent Service

Simplified client for fetching areas, services, and config from Home Assistant.
Supports both REST API and WebSocket API (2025 best practice).
"""

import asyncio
import json
import logging
from typing import Any

import aiohttp
import websockets
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """
    Client for interacting with Home Assistant API.
    
    Supports both REST API and WebSocket API (2025 best practice).
    WebSocket API is preferred for area registry access.
    """

    def __init__(
        self,
        ha_url: str,
        access_token: str,
        timeout: int = 10
    ):
        """
        Initialize HA client.

        Args:
            ha_url: Home Assistant URL (e.g., "http://homeassistant:8123")
            access_token: Long-lived access token from HA
            timeout: Request timeout in seconds
        """
        self.ha_url = ha_url.rstrip('/')
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a reusable client session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                headers=self.headers,
                timeout=self.timeout
            )
        return self._session

    async def _get_area_registry_websocket(self) -> list[dict[str, Any]]:
        """
        Get area registry using WebSocket API (2025 best practice).
        
        Uses WebSocket command: {"type": "config/area_registry/list"}
        This is the official, recommended method for accessing area registry.
        
        Returns:
            List of area dictionaries with keys: area_id, name, aliases, etc.
            
        Raises:
            Exception: If WebSocket connection or command fails
        """
        # Convert HTTP URL to WebSocket URL
        ws_url = self.ha_url.replace('http://', 'ws://').replace('https://', 'wss://')
        ws_url = f"{ws_url}/api/websocket"
        
        try:
            logger.debug(f"🔌 Connecting to Home Assistant WebSocket: {ws_url}")
            
            # Connect to WebSocket (authentication happens via messages, not headers)
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                # Handle authentication
                auth_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                auth_data = json.loads(auth_response)
                
                if auth_data.get("type") == "auth_required":
                    logger.debug("🔐 Authentication required, sending token...")
                    await websocket.send(json.dumps({"type": "auth", "access_token": self.access_token}))
                    
                    auth_result = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    auth_result_data = json.loads(auth_result)
                    
                    if auth_result_data.get("type") != "auth_ok":
                        raise Exception(f"WebSocket authentication failed: {auth_result_data}")
                    logger.debug("✅ WebSocket authenticated")
                elif auth_data.get("type") != "auth_ok":
                    raise Exception(f"Unexpected WebSocket auth response: {auth_data}")
                
                # Send area registry list command
                message_id = 1
                command = {
                    "id": message_id,
                    "type": "config/area_registry/list"
                }
                await websocket.send(json.dumps(command))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                # Parse response
                if response_data.get("id") == message_id and response_data.get("type") == "result":
                    if not response_data.get("success", False):
                        error = response_data.get("error", {})
                        raise Exception(f"WebSocket command failed: {error.get('message', 'Unknown error')}")
                    
                    # Extract areas from result
                    areas = response_data.get("result", [])
                    logger.info(f"✅ Fetched {len(areas)} areas via WebSocket API")
                    return areas
                else:
                    raise Exception(f"Unexpected WebSocket response format: {response_data}")
                    
        except asyncio.TimeoutError:
            raise Exception("WebSocket connection or response timeout")
        except websockets.exceptions.InvalidStatusCode as e:
            raise Exception(f"WebSocket connection failed: {e}")
        except Exception as e:
            raise Exception(f"WebSocket error: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def get_area_registry(self) -> list[dict[str, Any]]:
        """
        Get area registry from Home Assistant.
        
        2025 Best Practice: Tries WebSocket API first (official method),
        falls back to REST API if WebSocket fails.

        Returns:
            List of area dictionaries with keys: area_id, name, aliases, etc.

        Raises:
            Exception: If both WebSocket and REST API requests fail
        """
        # Try WebSocket API first (2025 best practice)
        try:
            logger.debug("🔌 Attempting to fetch area registry via WebSocket API...")
            return await self._get_area_registry_websocket()
        except Exception as ws_error:
            logger.warning(f"⚠️ WebSocket API failed: {ws_error}")
            logger.info("🔄 Falling back to REST API...")
            
            # Fallback to REST API
            try:
                session = await self._get_session()
                url = f"{self.ha_url}/api/config/area_registry/list"

                async with session.get(url) as response:
                    if response.status == 404:
                        # REST endpoint not available
                        logger.info("ℹ️ Area Registry REST API not available (404) - returning empty list")
                        return []
                    response.raise_for_status()
                    data = await response.json()
                    # Handle both list format and dict with 'areas' key
                    if isinstance(data, dict) and "areas" in data:
                        areas = data["areas"]
                    elif isinstance(data, list):
                        areas = data
                    else:
                        areas = []
                    logger.info(f"✅ Fetched {len(areas)} areas from Home Assistant via REST API")
                    return areas
            except aiohttp.ClientError as e:
                error_msg = f"Failed to fetch area registry (both WebSocket and REST failed): {str(e)}"
                logger.error(f"❌ {error_msg}")
                raise Exception(error_msg) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def get_services(self) -> dict[str, Any]:
        """
        Get available services from Home Assistant.

        Returns:
            Dictionary of services grouped by domain

        Raises:
            Exception: If API request fails
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/services"

            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.info("✅ Fetched services from Home Assistant")
                return data
        except aiohttp.ClientError as e:
            error_msg = f"Failed to fetch services: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def get_states(self) -> list[dict[str, Any]]:
        """
        Get all entity states from Home Assistant.

        Uses REST API endpoint: GET /api/states
        Reference: https://developers.home-assistant.io/docs/api/rest/

        Returns:
            List of state dictionaries with entity_id, state, attributes, etc.

        Raises:
            Exception: If API request fails
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/states"

            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.debug(f"✅ Fetched {len(data)} entity states from Home Assistant")
                return data
        except aiohttp.ClientError as e:
            error_msg = f"Failed to fetch states: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def get_helpers(self) -> list[dict[str, Any]]:
        """
        Get helpers (input_boolean, input_number, input_select, etc.) from Home Assistant.

        Filters states by helper domains. Helpers are entities with domains:
        - input_boolean
        - input_number
        - input_select
        - input_text
        - input_datetime
        - input_button
        - counter
        - timer

        Returns:
            List of helper state dictionaries with entity_id, state, attributes

        Raises:
            Exception: If API request fails
        """
        try:
            all_states = await self.get_states()
            helper_domains = {
                "input_boolean", "input_number", "input_select", "input_text",
                "input_datetime", "input_button", "counter", "timer"
            }

            helpers = []
            for state in all_states:
                entity_id = state.get("entity_id", "")
                if entity_id:
                    domain = entity_id.split(".")[0]
                    if domain in helper_domains:
                        helpers.append({
                            "id": entity_id.split(".", 1)[1] if "." in entity_id else entity_id,
                            "type": domain,
                            "entity_id": entity_id,
                            "name": state.get("attributes", {}).get("friendly_name", entity_id),
                            "state": state.get("state")
                        })

            logger.info(f"✅ Found {len(helpers)} helpers from Home Assistant")
            return helpers
        except Exception as e:
            error_msg = f"Failed to fetch helpers: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def get_scenes(self) -> list[dict[str, Any]]:
        """
        Get scenes from Home Assistant.

        Filters states by scene domain. Scenes are entities with domain "scene".

        Returns:
            List of scene state dictionaries with entity_id, state, attributes

        Raises:
            Exception: If API request fails
        """
        try:
            all_states = await self.get_states()

            scenes = []
            for state in all_states:
                entity_id = state.get("entity_id", "")
                if entity_id and entity_id.startswith("scene."):
                    scenes.append({
                        "id": entity_id.split(".", 1)[1] if "." in entity_id else entity_id,
                        "entity_id": entity_id,
                        "name": state.get("attributes", {}).get("friendly_name", entity_id),
                        "state": state.get("state")
                    })

            logger.info(f"✅ Found {len(scenes)} scenes from Home Assistant")
            return scenes
        except Exception as e:
            error_msg = f"Failed to fetch scenes: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e

    async def _get_device_registry_websocket(self) -> list[dict[str, Any]]:
        """
        Get device registry using WebSocket API (2025 best practice).
        
        Uses WebSocket command: {"type": "config/device_registry/list"}
        This is the official, recommended method for accessing device registry.
        
        Returns:
            List of device dictionaries with keys: id, name, area_id, manufacturer, model, etc.
            
        Raises:
            Exception: If WebSocket connection or command fails
        """
        # Convert HTTP URL to WebSocket URL
        ws_url = self.ha_url.replace('http://', 'ws://').replace('https://', 'wss://')
        ws_url = f"{ws_url}/api/websocket"
        
        try:
            logger.debug(f"🔌 Connecting to Home Assistant WebSocket: {ws_url}")
            
            # Connect to WebSocket (authentication happens via messages, not headers)
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                # Handle authentication
                auth_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                auth_data = json.loads(auth_response)
                
                if auth_data.get("type") == "auth_required":
                    logger.debug("🔐 Authentication required, sending token...")
                    await websocket.send(json.dumps({"type": "auth", "access_token": self.access_token}))
                    
                    auth_result = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    auth_result_data = json.loads(auth_result)
                    
                    if auth_result_data.get("type") != "auth_ok":
                        raise Exception(f"WebSocket authentication failed: {auth_result_data}")
                    logger.debug("✅ WebSocket authenticated")
                elif auth_data.get("type") != "auth_ok":
                    raise Exception(f"Unexpected WebSocket auth response: {auth_data}")
                
                # Send device registry list command
                message_id = 2
                command = {
                    "id": message_id,
                    "type": "config/device_registry/list"
                }
                await websocket.send(json.dumps(command))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                # Parse response
                if response_data.get("id") == message_id and response_data.get("type") == "result":
                    if not response_data.get("success", False):
                        error = response_data.get("error", {})
                        raise Exception(f"WebSocket command failed: {error.get('message', 'Unknown error')}")
                    
                    # Extract devices from result
                    devices = response_data.get("result", [])
                    logger.info(f"✅ Fetched {len(devices)} devices via WebSocket API")
                    return devices
                else:
                    raise Exception(f"Unexpected WebSocket response format: {response_data}")
                    
        except asyncio.TimeoutError:
            raise Exception("WebSocket connection or response timeout")
        except websockets.exceptions.InvalidStatusCode as e:
            raise Exception(f"WebSocket connection failed: {e}")
        except Exception as e:
            raise Exception(f"WebSocket error: {str(e)}")

    async def _get_entity_registry_websocket(self) -> list[dict[str, Any]]:
        """
        Get entity registry using WebSocket API (2025 best practice).
        
        Uses WebSocket command: {"type": "config/entity_registry/list"}
        This is the official, recommended method for accessing entity registry.
        
        Returns:
            List of entity registry dictionaries with keys: entity_id, aliases, category, etc.
            
        Raises:
            Exception: If WebSocket connection or command fails
        """
        # Convert HTTP URL to WebSocket URL
        ws_url = self.ha_url.replace('http://', 'ws://').replace('https://', 'wss://')
        ws_url = f"{ws_url}/api/websocket"
        
        try:
            logger.debug(f"🔌 Connecting to Home Assistant WebSocket: {ws_url}")
            
            # Connect to WebSocket (authentication happens via messages, not headers)
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                # Handle authentication
                auth_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                auth_data = json.loads(auth_response)
                
                if auth_data.get("type") == "auth_required":
                    logger.debug("🔐 Authentication required, sending token...")
                    await websocket.send(json.dumps({"type": "auth", "access_token": self.access_token}))
                    
                    auth_result = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    auth_result_data = json.loads(auth_result)
                    
                    if auth_result_data.get("type") != "auth_ok":
                        raise Exception(f"WebSocket authentication failed: {auth_result_data}")
                    logger.debug("✅ WebSocket authenticated")
                elif auth_data.get("type") != "auth_ok":
                    raise Exception(f"Unexpected WebSocket auth response: {auth_data}")
                
                # Send entity registry list command
                message_id = 3
                command = {
                    "id": message_id,
                    "type": "config/entity_registry/list"
                }
                await websocket.send(json.dumps(command))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                # Parse response
                if response_data.get("id") == message_id and response_data.get("type") == "result":
                    if not response_data.get("success", False):
                        error = response_data.get("error", {})
                        raise Exception(f"WebSocket command failed: {error.get('message', 'Unknown error')}")
                    
                    # Extract entities from result
                    entities = response_data.get("result", [])
                    logger.info(f"✅ Fetched {len(entities)} entities via WebSocket API")
                    return entities
                else:
                    raise Exception(f"Unexpected WebSocket response format: {response_data}")
                    
        except asyncio.TimeoutError:
            raise Exception("WebSocket connection or response timeout")
        except websockets.exceptions.InvalidStatusCode as e:
            raise Exception(f"WebSocket connection failed: {e}")
        except Exception as e:
            raise Exception(f"WebSocket error: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def get_entity_registry(self) -> list[dict[str, Any]]:
        """
        Get entity registry from Home Assistant.
        
        2025 Best Practice: Tries WebSocket API first (official method),
        falls back to REST API if WebSocket fails.

        Returns:
            List of entity registry dictionaries with keys: entity_id, aliases, category, disabled_by, etc.

        Raises:
            Exception: If both WebSocket and REST API requests fail
        """
        # Try WebSocket API first (2025 best practice)
        try:
            logger.debug("🔌 Attempting to fetch entity registry via WebSocket API...")
            return await self._get_entity_registry_websocket()
        except Exception as ws_error:
            logger.warning(f"⚠️ WebSocket API failed: {ws_error}")
            logger.info("🔄 Falling back to REST API...")
            
            # Fallback to REST API
            try:
                session = await self._get_session()
                url = f"{self.ha_url}/api/config/entity_registry/list"

                async with session.get(url) as response:
                    if response.status == 404:
                        # REST endpoint not available
                        logger.info("ℹ️ Entity Registry REST API not available (404) - returning empty list")
                        return []
                    response.raise_for_status()
                    data = await response.json()
                    # Handle both list format and dict with 'entities' key
                    if isinstance(data, dict) and "entities" in data:
                        entities = data["entities"]
                    elif isinstance(data, list):
                        entities = data
                    else:
                        entities = []
                    logger.info(f"✅ Fetched {len(entities)} entities from Home Assistant via REST API")
                    return entities
            except aiohttp.ClientError as e:
                error_msg = f"Failed to fetch entity registry (both WebSocket and REST failed): {str(e)}"
                logger.error(f"❌ {error_msg}")
                raise Exception(error_msg) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def get_device_registry(self) -> list[dict[str, Any]]:
        """
        Get device registry from Home Assistant.
        
        2025 Best Practice: Tries WebSocket API first (official method),
        falls back to REST API if WebSocket fails.

        Returns:
            List of device dictionaries with keys: id, name, area_id, manufacturer, model, etc.

        Raises:
            Exception: If both WebSocket and REST API requests fail
        """
        # Try WebSocket API first (2025 best practice)
        try:
            logger.debug("🔌 Attempting to fetch device registry via WebSocket API...")
            return await self._get_device_registry_websocket()
        except Exception as ws_error:
            logger.warning(f"⚠️ WebSocket API failed: {ws_error}")
            logger.info("🔄 Falling back to REST API...")
            
            # Fallback to REST API
            try:
                session = await self._get_session()
                url = f"{self.ha_url}/api/config/device_registry/list"

                async with session.get(url) as response:
                    if response.status == 404:
                        # REST endpoint not available
                        logger.info("ℹ️ Device Registry REST API not available (404) - returning empty list")
                        return []
                    response.raise_for_status()
                    data = await response.json()
                    # Handle both list format and dict with 'devices' key
                    if isinstance(data, dict) and "devices" in data:
                        devices = data["devices"]
                    elif isinstance(data, list):
                        devices = data
                    else:
                        devices = []
                    logger.info(f"✅ Fetched {len(devices)} devices from Home Assistant via REST API")
                    return devices
            except aiohttp.ClientError as e:
                error_msg = f"Failed to fetch device registry (both WebSocket and REST failed): {str(e)}"
                logger.error(f"❌ {error_msg}")
                raise Exception(error_msg) from e

    async def close(self):
        """Close HTTP client connection pool"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("✅ Home Assistant client closed")

