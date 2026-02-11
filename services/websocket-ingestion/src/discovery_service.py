"""
Home Assistant Device & Entity Discovery Service

Queries Home Assistant registries to discover connected devices, entities, and integrations.
Epic 50 Story 50.2: Added configurable SSL verification
"""

import asyncio
import logging
import os
import time
from typing import Any

from aiohttp import ClientWebSocketResponse

from .message_id_manager import get_message_id_manager
from .models import Device, Entity

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service for discovering devices and entities from Home Assistant registries"""

    def __init__(self, influxdb_manager=None):
        self.message_id_manager = get_message_id_manager()  # Use centralized manager
        self.pending_responses: dict[int, asyncio.Future] = {}  # Message routing: message_id -> Future
        self.influxdb_manager = influxdb_manager

        # Epic 23.2: Device and area mapping caches for event enrichment
        self.entity_to_device: dict[str, str] = {}  # entity_id → device_id
        self.device_to_area: dict[str, str] = {}    # device_id → area_id
        self.entity_to_area: dict[str, str] = {}    # entity_id → area_id (direct assignment)
        self.device_metadata: dict[str, dict[str, Any]] = {}  # device_id → {manufacturer, model, sw_version}

        # Cache expiration tracking (refresh every 30 minutes to handle stale data)
        self._cache_timestamp: float | None = None
        self._cache_ttl_seconds = 1800  # 30 minutes - devices/areas don't change often
        self._last_stale_warning_timestamp: float | None = None  # Track when we last warned about stale cache
        self._stale_warning_interval = 600  # Only warn every 10 minutes to avoid log spam

        logger.info("Discovery service initialized with device/area mapping caches")

    async def _get_next_id(self) -> int:
        """Get next message ID from centralized manager"""
        return await self.message_id_manager.get_next_id()

    async def _discover_devices_websocket(self, websocket: ClientWebSocketResponse | None = None, connection_manager = None) -> list[dict[str, Any]]:
        """
        Discover devices via WebSocket using message routing
        
        Uses message routing through connection manager to avoid listen loop conflicts.
        
        Args:
            websocket: Connected WebSocket client (optional, for backward compatibility)
            connection_manager: Connection manager for sending messages (preferred)
            
        Returns:
            List of device dictionaries
        """
        try:
            message_id = await self._get_next_id()
            logger.info("📱 Discovering devices via WebSocket (using message routing)...")

            # Use connection manager if available (preferred method)
            if connection_manager:
                message = {
                    "id": message_id,
                    "type": "config/device_registry/list"
                }
                if not await connection_manager.send_message(message):
                    logger.error("❌ Failed to send device registry command via connection manager")
                    return []
            elif websocket:
                # Fallback to direct websocket send (for backward compatibility)
                await websocket.send_json({
                    "id": message_id,
                    "type": "config/device_registry/list"
                })
            else:
                logger.error("❌ No websocket or connection manager provided")
                return []

            # Wait for response using message routing (works with listen loop)
            response = await self._wait_for_response(websocket, message_id, timeout=10.0)

            if not response or not response.get("success"):
                error_msg = response.get("error", {}).get("message", "Unknown error") if response else "No response"
                logger.error(f"❌ Device registry command failed: {error_msg}")
                return []

            devices = response.get("result", [])
            logger.info(f"✅ Discovered {len(devices)} devices via WebSocket")
            return devices

        except Exception as e:
            logger.error(f"❌ Error discovering devices via WebSocket: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def _discover_devices_http(self) -> list[dict[str, Any]]:
        """
        Discover devices via HTTP API (fallback when WebSocket not available)
        
        Uses Home Assistant's HTTP API endpoint: /api/config/device_registry/list
        
        Returns:
            List of device dictionaries
        """
        try:
            import os
            import aiohttp

            ha_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123')
            ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')

            if not ha_token:
                logger.warning("⚠️  No HA token available for HTTP device discovery")
                return []

            # Normalize URL (ensure http:// not ws://)
            ha_url = ha_url.replace('ws://', 'http://').replace('wss://', 'https://').rstrip('/')

            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json"
            }

            logger.info(f"🔗 Fetching devices from HTTP API: {ha_url}/api/config/device_registry/list")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{ha_url}/api/config/device_registry/list",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        devices = data.get("devices", [])
                        logger.info(f"✅ Retrieved {len(devices)} devices via HTTP API")
                        return devices
                    elif response.status == 404:
                        logger.warning("⚠️  Device Registry HTTP API not available (404) - endpoint may not exist in this HA version")
                        return []
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ HTTP Device Registry API failed: HTTP {response.status} - {error_text[:200]}")
                        return []
        except Exception as e:
            logger.error(f"❌ Error discovering devices via HTTP API: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def discover_devices(self, websocket: ClientWebSocketResponse | None = None, connection_manager = None) -> list[dict[str, Any]]:
        """
        Discover all devices from Home Assistant device registry
        
        Tries WebSocket first, then falls back to HTTP API if available.
        
        Args:
            websocket: Optional WebSocket client (preferred method)
            
        Returns:
            List of device dictionaries
        """
        try:
            logger.info("=" * 80)
            logger.info("📱 DISCOVERING DEVICES")
            logger.info("=" * 80)

            # Try WebSocket first (preferred method) - use message routing to avoid listen loop conflicts
            devices = []
            if connection_manager:
                logger.info("Using WebSocket for device discovery (with message routing)")
                devices = await self._discover_devices_websocket(websocket, connection_manager)
                if not devices:
                    logger.warning("WebSocket device discovery returned empty - trying HTTP API fallback")
            elif websocket:
                logger.info("Using WebSocket for device discovery (legacy mode)")
                devices = await self._discover_devices_websocket(websocket, None)
                if not devices:
                    logger.warning("WebSocket device discovery returned empty - trying HTTP API fallback")

            # Fallback to HTTP API if WebSocket not available or failed
            if not devices:
                logger.info("Attempting HTTP API for device discovery (fallback)")
                devices = await self._discover_devices_http()

            if not devices:
                logger.warning("⚠️  Both WebSocket and HTTP API failed - no devices discovered")
                logger.info("💡 Device info will be available from entity registry (device_id references)")
                return []

            device_count = len(devices)
            logger.info(f"✅ Discovered {device_count} devices")

            # Epic 23.2: Build device -> area mapping cache
            # Epic 23.5: Build device metadata cache
            for device in devices:
                device_id = device.get("id")
                if device_id:
                    # Store device -> area mapping
                    area_id = device.get("area_id")
                    if area_id:
                        self.device_to_area[device_id] = area_id

                    # Epic 23.5: Store device metadata (manufacturer, model, version)
                    self.device_metadata[device_id] = {
                        "manufacturer": device.get("manufacturer"),
                        "model": device.get("model"),
                        "sw_version": device.get("sw_version"),
                        "name": device.get("name"),
                        "name_by_user": device.get("name_by_user")
                    }

            logger.info(f"Cached {len(self.device_to_area)} device -> area mappings")
            logger.info(f"Cached {len(self.device_metadata)} device metadata entries")

            # Update cache timestamp
            self._cache_timestamp = time.time()

            # Log sample device if available
            if devices:
                sample = devices[0]
                logger.info(f"Sample device: {sample.get('name', 'Unknown')} "
                          f"(manufacturer: {sample.get('manufacturer', 'Unknown')}, "
                          f"model: {sample.get('model', 'Unknown')})")

            return devices

        except Exception as e:
            logger.error(f"❌ Error discovering devices: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def _discover_entities_http(self) -> list[dict[str, Any]]:
        """
        Discover entities via HTTP States API (fallback when WebSocket not available)

        WARNING: The /api/states endpoint does NOT return entity registry metadata
        (device_id, area_id, name, name_by_user, original_name, unique_id, etc.).
        Entities discovered via this method will have device_id=None, meaning they
        won't appear when querying entities by device. Use WebSocket entity registry
        as the primary method whenever possible.

        Returns:
            List of entity dictionaries (minimal: entity_id + platform only)
        """
        try:
            import os

            import aiohttp

            ha_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123')
            ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')

            if not ha_token:
                logger.warning("⚠️  No HA token available for HTTP entity discovery")
                return []

            ha_url = ha_url.replace('ws://', 'http://').replace('wss://', 'https://').rstrip('/')

            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json"
            }

            ssl_verify = os.getenv('SSL_VERIFY', 'true').lower() in ('true', '1', 'yes', 'on')
            connector = aiohttp.TCPConnector(ssl=ssl_verify)
            async with aiohttp.ClientSession(connector=connector) as session:
                logger.info(f"📡 Fetching entities from States API: {ha_url}/api/states")
                async with session.get(
                    f"{ha_url}/api/states",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ HTTP States API failed: HTTP {response.status} - {error_text[:200]}")
                        return []

                    states = await response.json()
                    entities = []
                    for state in states:
                        entity_id = state.get("entity_id")
                        if entity_id:
                            domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
                            entities.append({
                                "entity_id": entity_id,
                                "platform": domain,
                                # NOTE: States API does NOT provide device_id, area_id,
                                # name, name_by_user, original_name, unique_id, etc.
                            })

                    logger.info(f"✅ Retrieved {len(entities)} entities via HTTP States API")
                    logger.warning("⚠️  HTTP States API does not provide device_id - entities won't link to devices")
                    return entities

        except Exception as e:
            logger.error(f"❌ Error discovering entities via HTTP API: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def discover_entities(self, websocket: ClientWebSocketResponse | None = None, connection_manager=None) -> list[dict[str, Any]]:
        """
        Discover all entities from Home Assistant entity registry

        Tries WebSocket entity registry first (provides complete metadata including
        device_id, area_id, names), then falls back to HTTP States API.

        Args:
            websocket: Optional WebSocket client (preferred method)
            connection_manager: Connection manager for sending messages (preferred over raw websocket)

        Returns:
            List of entity dictionaries
        """
        try:
            logger.info("=" * 80)
            logger.info("🔌 DISCOVERING ENTITIES")
            logger.info("=" * 80)

            # Try WebSocket entity registry first (preferred - has complete metadata including device_id)
            entities = []
            if connection_manager or websocket:
                logger.info("Using WebSocket entity registry for entity discovery (has device_id, names, etc.)")
                entities = await self._discover_entities_websocket(websocket, connection_manager)
                if not entities:
                    logger.warning("WebSocket entity discovery returned empty - trying HTTP States API fallback")

            # Fallback to HTTP States API if WebSocket not available or failed
            if not entities:
                logger.info("Attempting HTTP States API for entity discovery (fallback - no device_id)")
                entities = await self._discover_entities_http()

            if not entities:
                logger.warning("⚠️  Both WebSocket and HTTP API failed - no entities discovered")
                return []

            entity_count = len(entities)
            logger.info(f"✅ Discovered {entity_count} entities")

            # Epic 23.2: Build entity → device and entity → area mapping caches
            for entity in entities:
                entity_id = entity.get("entity_id")
                if entity_id:
                    device_id = entity.get("device_id")
                    if device_id:
                        self.entity_to_device[entity_id] = device_id

                    area_id = entity.get("area_id")
                    if area_id:
                        self.entity_to_area[entity_id] = area_id

            logger.info(f"🔗 Cached {len(self.entity_to_device)} entity → device mappings")
            logger.info(f"📍 Cached {len(self.entity_to_area)} entity → area mappings (direct)")

            # Update cache timestamp
            self._cache_timestamp = time.time()

            # Log sample entity if available
            if entities:
                sample = entities[0]
                entity_id = sample.get('entity_id', 'Unknown')
                domain = entity_id.split('.')[0] if '.' in entity_id else 'Unknown'
                logger.info(f"🔌 Sample entity: {entity_id} "
                          f"(platform: {sample.get('platform', 'Unknown')}, "
                          f"device_id: {sample.get('device_id', 'None')}, "
                          f"domain: {domain})")
                logger.info(f"   name: {sample.get('name')}, "
                          f"name_by_user: {sample.get('name_by_user')}, "
                          f"original_name: {sample.get('original_name')}")

            return entities

        except Exception as e:
            logger.error(f"❌ Error discovering entities: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def _discover_entities_websocket(self, websocket: ClientWebSocketResponse | None = None, connection_manager=None) -> list[dict[str, Any]]:
        """
        Discover entities via WebSocket entity registry (primary method)

        Uses config/entity_registry/list which returns complete metadata:
        device_id, area_id, name, name_by_user, original_name, unique_id, etc.

        Args:
            websocket: Connected WebSocket client (optional, for backward compatibility)
            connection_manager: Connection manager for sending messages (preferred)

        Returns:
            List of entity dictionaries with full registry metadata
        """
        try:
            message_id = await self._get_next_id()
            logger.info("🔌 Discovering entities via WebSocket entity registry...")

            # Use connection manager if available (preferred method)
            if connection_manager:
                message = {
                    "id": message_id,
                    "type": "config/entity_registry/list"
                }
                if not await connection_manager.send_message(message):
                    logger.error("❌ Failed to send entity registry command via connection manager")
                    return []
            elif websocket:
                await websocket.send_json({
                    "id": message_id,
                    "type": "config/entity_registry/list"
                })
            else:
                logger.error("❌ No websocket or connection manager provided")
                return []

            # Wait for response
            response = await self._wait_for_response(websocket, message_id, timeout=10.0)

            if not response or not response.get("success"):
                error_msg = response.get("error", {}).get("message", "Unknown error") if response else "No response"
                logger.error(f"❌ Entity registry WebSocket command failed: {error_msg}")
                return []

            entities = response.get("result", [])
            logger.info(f"✅ Discovered {len(entities)} entities via WebSocket entity registry")
            return entities

        except Exception as e:
            logger.error(f"❌ Error discovering entities via WebSocket: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def discover_config_entries(self, websocket: ClientWebSocketResponse | None = None, connection_manager = None) -> list[dict[str, Any]]:
        """
        Discover all config entries (integrations) from Home Assistant
        
        Args:
            websocket: Connected WebSocket client
            
        Returns:
            List of config entry dictionaries
            
        Raises:
            Exception: If command fails or response is invalid
        """
        try:
            message_id = await self._get_next_id()
            logger.info("=" * 80)
            logger.info(f"🔧 DISCOVERING CONFIG ENTRIES (message_id: {message_id})")
            logger.info("=" * 80)

            # Send config entries list command (use connection_manager if available)
            if connection_manager:
                message = {
                    "id": message_id,
                    "type": "config_entries/list"
                }
                if not await connection_manager.send_message(message):
                    logger.error("❌ Failed to send config entries command via connection manager")
                    return []
            elif websocket:
                await websocket.send_json({
                    "id": message_id,
                    "type": "config_entries/list"
                })
            else:
                logger.error("❌ No websocket or connection manager provided")
                return []

            logger.info("✅ Config entries command sent, waiting for response...")

            # Wait for response using message routing
            response = await self._wait_for_response(websocket, message_id, timeout=10.0)

            if not response:
                logger.error("❌ No response received for config entries command")
                return []

            if not response.get("success"):
                error_msg = response.get("error", {}).get("message", "Unknown error")
                logger.error(f"❌ Config entries command failed: {error_msg}")
                return []

            config_entries = response.get("result", [])
            entry_count = len(config_entries)

            logger.info(f"✅ Discovered {entry_count} config entries")

            # Log sample config entry if available
            if config_entries:
                sample = config_entries[0]
                logger.info(f"🔧 Sample config entry: {sample.get('title', 'Unknown')} "
                          f"(domain: {sample.get('domain', 'Unknown')}, "
                          f"state: {sample.get('state', 'Unknown')})")

            return config_entries

        except asyncio.TimeoutError:
            logger.error("❌ Timeout waiting for config entries response")
            return []
        except Exception as e:
            logger.error(f"❌ Error discovering config entries: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def _wait_for_response(
        self,
        websocket: ClientWebSocketResponse | None,
        message_id: int,
        timeout: float = 10.0
    ) -> dict[str, Any] | None:
        """
        Wait for response with specific message ID using message routing
        
        Uses pending_responses dict to route messages from connection manager's listen loop.
        This allows discovery to work even when listen loop is active.
        
        Args:
            websocket: WebSocket connection (optional - kept for compatibility)
            message_id: Message ID to wait for
            timeout: Timeout in seconds
            
        Returns:
            Response dictionary or None if timeout/error
        """
        try:
            # Create Future for this message ID (message routing pattern)
            future = asyncio.Future()
            self.pending_responses[message_id] = future
            
            try:
                # Wait for response via Future (will be set by handle_message_result)
                # Device registry queries can be slow, use extended timeout
                extended_timeout = timeout * 1.5  # 15 seconds for device registry
                response = await asyncio.wait_for(future, timeout=extended_timeout)
                # Clean up Future only on success
                self.pending_responses.pop(message_id, None)
                logger.debug(f"✅ Received response for message {message_id}")
                return response
            except asyncio.TimeoutError:
                logger.warning(f"⚠️  Timeout waiting for message {message_id} (waited {extended_timeout}s) - message may arrive late")
                # Don't remove Future immediately - message might arrive late
                # Clean up after a delay to allow late messages (but don't block)
                if message_id in self.pending_responses:
                    # Schedule cleanup in background
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self._cleanup_pending_response(message_id, delay=2.0))
                    except RuntimeError:
                        # Event loop not available, clean up immediately
                        self.pending_responses.pop(message_id, None)
                return None
                
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
            self.pending_responses.pop(message_id, None)
            return None
    
    async def _cleanup_pending_response(self, message_id: int, delay: float = 2.0):
        """Clean up pending response Future after a delay (for late-arriving messages)"""
        await asyncio.sleep(delay)
        self.pending_responses.pop(message_id, None)
    
    def handle_message_result(self, message: dict[str, Any]) -> bool:
        """
        Handle result message from connection manager's message routing
        
        This method is called by connection manager's _on_message handler
        to route result messages to pending discovery requests.
        
        Args:
            message: Message dictionary from WebSocket
            
        Returns:
            True if message was routed to a pending request, False otherwise
        """
        # Handle both "result" type messages and successful responses
        message_type = message.get("type")
        message_id = message.get("id")
        
        # Route result messages to pending discovery requests
        if message_type == "result" and message_id is not None:
            if message_id in self.pending_responses:
                future = self.pending_responses[message_id]
                if not future.done():
                    future.set_result(message)
                    logger.debug(f"✅ Routed result message {message_id} to pending discovery request")
                    return True
                else:
                    # Future already done (probably timed out), but message arrived
                    logger.debug(f"⚠️  Result message {message_id} arrived but Future already done (likely timeout)")
        
        return False

    async def discover_all(self, websocket: ClientWebSocketResponse | None = None, connection_manager = None, store: bool = True) -> dict[str, Any]:
        """
        Discover all devices, entities, config entries, and services

        Uses WebSocket registry commands first (full metadata), HTTP API as fallback.

        Args:
            websocket: Optional WebSocket client
            connection_manager: Connection manager for sending messages (preferred)
            store: Whether to store results in SQLite via data-api (default: True)

        Returns:
            Dictionary with 'devices', 'entities', 'config_entries', and 'services' keys
        """
        logger.info("=" * 80)
        logger.info("🚀 STARTING COMPLETE HOME ASSISTANT DISCOVERY")
        logger.info("=" * 80)

        # Discover devices and entities (WebSocket first, HTTP fallback)
        devices_data = await self.discover_devices(websocket, connection_manager)
        entities_data = await self.discover_entities(websocket, connection_manager)
        # Discover config entries to resolve integration names from config_entry_ids
        config_entries_data = await self.discover_config_entries(websocket, connection_manager) if (websocket or connection_manager) else []

        # Discover services from HA Services API (Epic 2025) - already uses HTTP API
        services_data = await self.discover_services(websocket)

        logger.info("=" * 80)
        logger.info("✅ DISCOVERY COMPLETE")
        logger.info(f"   Devices: {len(devices_data)}")
        logger.info(f"   Entities: {len(entities_data)}")
        logger.info(f"   Config Entries: {len(config_entries_data)}")
        logger.info(f"   Services: {len(services_data)} domains")
        logger.info("=" * 80)

        # Convert to models and store if requested
        # CRITICAL FIX: Always store to SQLite via data-api when store=True, regardless of influxdb_manager
        if store:
            logger.info("💾 Storing discovered data to SQLite via data-api...")
            logger.info(f"   Devices: {len(devices_data)}, Entities: {len(entities_data)}, Services: {len(services_data)}")
            await self.store_discovery_results(devices_data, entities_data, config_entries_data, services_data)
        else:
            logger.info("ℹ️  Storage disabled - skipping store_discovery_results")

        return {
            "devices": devices_data,
            "entities": entities_data,
            "config_entries": config_entries_data,
            "services": services_data
        }

    async def discover_services(self, websocket: ClientWebSocketResponse) -> dict[str, dict[str, Any]]:
        """
        Discover available services from Home Assistant Services API.
        
        Epic 2025: Fetch all available services per domain for service validation.
        
        Args:
            websocket: Connected WebSocket client
            
        Returns:
            Dictionary mapping domain -> {service_name -> service_data}
        """
        try:
            logger.info("🔍 Discovering services from HA Services API...")

            # Use HTTP API to fetch services (Services API doesn't have WebSocket command)
            import os

            import aiohttp

            ha_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123')
            ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')

            if not ha_token:
                logger.warning("⚠️  No HA token available for services discovery")
                return {}

            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ha_url}/api/services", headers=headers) as response:
                    if response.status == 200:
                        services_data = await response.json()
                        
                        # Handle list format: [{"domain": "light", "services": {...}}, ...]
                        # Transform to dict format: {"light": {...}, "lock": {...}}
                        if isinstance(services_data, list):
                            logger.debug(f"Converting services from list format ({len(services_data)} items) to dict format")
                            services_dict: dict[str, dict[str, Any]] = {}
                            for item in services_data:
                                if isinstance(item, dict) and "domain" in item and "services" in item:
                                    domain = item["domain"]
                                    services = item["services"]
                                    if isinstance(services, dict):
                                        services_dict[domain] = services
                            services_data = services_dict
                            logger.info(f"✅ Converted {len(services_dict)} service domains from list format")
                        elif not isinstance(services_data, dict):
                            logger.error(f"❌ Services data is neither dict nor list, got {type(services_data)}")
                            return {}
                        
                        # Validate structure - ensure it's dict[str, dict[str, Any]]
                        # Check that all values are dicts (domain services)
                        invalid_domains = []
                        for domain, domain_services in services_data.items():
                            if not isinstance(domain_services, dict):
                                invalid_domains.append(domain)
                        
                        if invalid_domains:
                            logger.warning(f"⚠️  Found {len(invalid_domains)} domains with invalid service format: {invalid_domains[:5]}")
                            # Filter out invalid domains
                            services_data = {k: v for k, v in services_data.items() if isinstance(v, dict)}
                        
                        logger.info(f"✅ Retrieved {len(services_data)} service domains from HA")
                        return services_data
                    else:
                        logger.warning(f"Failed to get services from HA: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error discovering services: {e}", exc_info=True)
            return {}

    async def store_discovery_results(
        self,
        devices_data: list[dict[str, Any]],
        entities_data: list[dict[str, Any]],
        config_entries_data: list[dict[str, Any]],
        services_data: dict[str, dict[str, Any]] = None
    ) -> bool:
        """
        Store discovery results to SQLite (via data-api) and optionally to InfluxDB
        
        Args:
            devices_data: List of device dictionaries from HA
            entities_data: List of entity dictionaries from HA
            config_entries_data: List of config entry dictionaries from HA
            
        Returns:
            True if storage successful
        """
        import os

        import aiohttp

        try:
            # Primary storage: SQLite via data-api (simple HTTP POST)
            # Use service name from docker-compose (data-api) as default
            data_api_url = os.getenv('DATA_API_URL', 'http://data-api:8006')
            api_key = os.getenv('DATA_API_API_KEY') or os.getenv('DATA_API_KEY') or os.getenv('API_KEY')

            # Create session with proper connector (disable SSL for internal HTTP)
            # Use connector_kwargs to ensure SSL is completely disabled
            connector = aiohttp.TCPConnector(
                ssl=False,
                limit=100,
                limit_per_host=30
            )
            timeout = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                connector_owner=True
            ) as session:
                # Build config_entry_id -> integration domain mapping
                config_entry_map: dict[str, str] = {}
                if config_entries_data:
                    for entry in config_entries_data:
                        entry_id = entry.get("entry_id")
                        domain = entry.get("domain")
                        if entry_id and domain:
                            config_entry_map[entry_id] = domain
                    logger.info(f"🔧 Built config entry mapping: {len(config_entry_map)} entries")
                
                # Resolve integration field for devices from config_entries
                if devices_data and config_entry_map:
                    for device in devices_data:
                        # Home Assistant device registry provides config_entries (array of IDs)
                        # but not integration field directly - we need to resolve it
                        if "integration" not in device or not device.get("integration"):
                            config_entries = device.get("config_entries", [])
                            if config_entries:
                                # Use first config entry to resolve integration
                                first_entry_id = config_entries[0] if isinstance(config_entries, list) else config_entries
                                integration = config_entry_map.get(first_entry_id)
                                if integration:
                                    device["integration"] = integration
                                    logger.debug(f"Resolved integration '{integration}' for device {device.get('name', 'unknown')} from config_entry {first_entry_id}")
                
                # Identify Zigbee devices within MQTT integration
                # Zigbee2MQTT devices use 'mqtt' integration but need to be identified as Zigbee
                if devices_data:
                    # Find Zigbee2MQTT Bridge device (to get its config_entry)
                    zigbee_bridge_config_entry = None
                    for device in devices_data:
                        manufacturer = str(device.get("manufacturer", "")).lower()
                        model = str(device.get("model", "")).lower()
                        name = str(device.get("name", "")).lower()
                        if "zigbee2mqtt" in manufacturer or ("bridge" in model and "zigbee" in name):
                            config_entries = device.get("config_entries", [])
                            if config_entries:
                                zigbee_bridge_config_entry = config_entries[0] if isinstance(config_entries, list) else config_entries
                                logger.info(f"🔍 Found Zigbee2MQTT Bridge with config_entry: {zigbee_bridge_config_entry}")
                                break
                    
                    # Identify Zigbee devices
                    # FIX: Check identifiers FIRST, even if integration is null
                    # This allows Zigbee devices to be identified even when config entries weren't discovered
                    zigbee_devices_found = 0
                    for device in devices_data:
                        integration = str(device.get("integration", "")).lower()
                        
                        is_zigbee = False
                        
                        # Method 1: Check device identifiers for Zigbee patterns (works even if integration is null)
                        identifiers = device.get("identifiers", [])
                        for identifier in identifiers:
                            identifier_str = str(identifier).lower()
                            # Check for 'zigbee' or 'ieee' in identifier
                            if 'zigbee' in identifier_str or 'ieee' in identifier_str:
                                is_zigbee = True
                                logger.debug(f"Identified {device.get('name', 'unknown')} as Zigbee (identifier pattern: {identifier_str})")
                                break
                            # Check for IEEE address pattern (0x followed by 8+ hex digits)
                            if identifier_str.startswith('0x') and len(identifier_str) >= 10:
                                # Check if it looks like an IEEE address (hexadecimal)
                                try:
                                    int(identifier_str[2:], 16)
                                    is_zigbee = True
                                    logger.debug(f"Identified {device.get('name', 'unknown')} as Zigbee (IEEE address pattern: {identifier_str})")
                                    break
                                except ValueError:
                                    pass
                        
                        # Method 2: Check if device shares config_entry with Zigbee2MQTT Bridge
                        if not is_zigbee and zigbee_bridge_config_entry:
                            config_entries = device.get("config_entries", [])
                            if config_entries:
                                device_entry = config_entries[0] if isinstance(config_entries, list) else config_entries
                                if device_entry == zigbee_bridge_config_entry:
                                    is_zigbee = True
                                    logger.debug(f"Identified {device.get('name', 'unknown')} as Zigbee (shares bridge config_entry)")
                        
                        # Method 3: If integration is already "mqtt", check if it's a Zigbee device
                        # (This is a fallback for devices that already have integration="mqtt" resolved)
                        if not is_zigbee and integration == "mqtt":
                            # Additional check: if device has via_device pointing to Zigbee bridge
                            via_device = device.get("via_device_id")
                            if via_device:
                                # Check if via_device is the Zigbee bridge
                                for bridge_device in devices_data:
                                    if bridge_device.get("id") == via_device:
                                        bridge_manufacturer = str(bridge_device.get("manufacturer", "")).lower()
                                        bridge_name = str(bridge_device.get("name", "")).lower()
                                        if "zigbee2mqtt" in bridge_manufacturer or "zigbee" in bridge_name:
                                            is_zigbee = True
                                            logger.debug(f"Identified {device.get('name', 'unknown')} as Zigbee (via Zigbee bridge device)")
                                            break
                        
                        if is_zigbee:
                            # Mark as Zigbee device
                            device["integration"] = "zigbee2mqtt"  # Update integration field
                            device["source"] = "zigbee2mqtt"  # Add source field for tracking
                            zigbee_devices_found += 1
                            logger.info(f"✅ Identified Zigbee device: {device.get('name', 'unknown')} (manufacturer: {device.get('manufacturer', 'unknown')})")
                    
                    if zigbee_devices_found > 0:
                        logger.info(f"🔍 Identified {zigbee_devices_found} Zigbee devices within MQTT integration")
                
                # Store devices to SQLite
                if devices_data:
                    try:
                        async with session.post(
                            f"{data_api_url}/internal/devices/bulk_upsert",
                            json=devices_data,
                            headers={"Authorization": f"Bearer {api_key}"} if api_key else None,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                logger.info(f"✅ Stored {result.get('upserted', 0)} devices to SQLite")
                            else:
                                error_text = await response.text()
                                logger.error(f"❌ Failed to store devices to SQLite: {response.status} - {error_text}")
                    except Exception as e:
                        logger.error(f"❌ Error posting devices to data-api: {e}")

                # Store entities to SQLite
                if entities_data:
                    try:
                        headers = {}
                        if api_key:
                            headers["Authorization"] = f"Bearer {api_key}"
                        headers["Content-Type"] = "application/json"

                        async with session.post(
                            f"{data_api_url}/internal/entities/bulk_upsert",
                            json=entities_data,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                logger.info(f"✅ Stored {result.get('upserted', 0)} entities to SQLite")
                            else:
                                error_text = await response.text()
                                logger.error(f"❌ Failed to store entities to SQLite: {response.status} - {error_text}")
                    except Exception as e:
                        logger.error(f"❌ Error posting entities to data-api: {e}")

                # Store services to SQLite (Epic 2025) - with graceful degradation
                if services_data:
                    try:
                        headers = {}
                        if api_key:
                            headers["Authorization"] = f"Bearer {api_key}"
                        headers["Content-Type"] = "application/json"

                        # First, check if endpoint exists (optional - graceful degradation)
                        endpoint_url = f"{data_api_url}/internal/services/bulk_upsert"

                        async with session.post(
                            endpoint_url,
                            json=services_data,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                logger.info(f"✅ Stored {result.get('upserted', 0)} services to SQLite")
                            elif response.status == 404:
                                # Endpoint doesn't exist - check if this is expected
                                # Log as warning but note it might indicate missing endpoint implementation
                                logger.warning("⚠️  Services bulk_upsert endpoint returned 404 (Not Found)")
                                logger.warning(f"   Endpoint: {endpoint_url}")
                                logger.warning("   This may indicate:")
                                logger.warning("   1. Endpoint not yet implemented in data-api (expected)")
                                logger.warning("   2. Incorrect endpoint URL (configuration issue)")
                                logger.warning("   Discovery will continue, but services will not be stored")
                            elif response.status == 401 or response.status == 403:
                                error_text = await response.text()
                                logger.error(f"❌ Services storage failed: Authentication/Authorization error ({response.status})")
                                logger.error(f"   Error: {error_text}")
                                logger.error("   Check DATA_API_API_KEY or DATA_API_KEY environment variable")
                            else:
                                error_text = await response.text()
                                logger.warning(f"⚠️  Failed to store services to SQLite: HTTP {response.status}")
                                logger.warning(f"   Error: {error_text}")
                                logger.warning("   Discovery will continue, but services will not be stored")
                    except Exception as e:
                        # Don't fail entire operation if services storage fails
                        logger.warning(f"⚠️  Error posting services to data-api: {e}")
                        logger.info("💡 Services storage error is non-critical - discovery will continue")

            # Optional: Store snapshot to InfluxDB for historical tracking
            store_influx_history = os.getenv('STORE_DEVICE_HISTORY_IN_INFLUXDB', 'false').lower() == 'true'

            if store_influx_history and self.influxdb_manager:
                logger.info("📊 Storing device history snapshot to InfluxDB...")

                # Convert devices to models for InfluxDB
                devices = []
                for device_data in devices_data:
                    try:
                        device = Device.from_ha_device(device_data)
                        device.validate()
                        devices.append(device)
                    except Exception as e:
                        logger.warning(f"⚠️  Skipping invalid device for InfluxDB: {e}")

                # Convert entities to models for InfluxDB
                entities = []
                for entity_data in entities_data:
                    try:
                        entity = Entity.from_ha_entity(entity_data)
                        entity.validate()
                        entities.append(entity)
                    except Exception as e:
                        logger.warning(f"⚠️  Skipping invalid entity for InfluxDB: {e}")

                # Batch write to InfluxDB
                if devices:
                    device_points = [d.to_influx_point() for d in devices]
                    success = await self.influxdb_manager.batch_write_devices(device_points, bucket="home_assistant_events")
                    if success:
                        logger.info(f"✅ Stored {len(devices)} devices history to InfluxDB")

                if entities:
                    entity_points = [e.to_influx_point() for e in entities]
                    success = await self.influxdb_manager.batch_write_entities(entity_points, bucket="home_assistant_events")
                    if success:
                        logger.info(f"✅ Stored {len(entities)} entities history to InfluxDB")

            logger.info("=" * 80)
            logger.info("✅ STORAGE COMPLETE")
            if services_data:
                # Fix: Handle both dict and list formats
                if isinstance(services_data, dict):
                    total_services = sum(len(domain_services) for domain_services in services_data.values())
                    logger.info(f"   Services: {total_services} total services across {len(services_data)} domains")
                elif isinstance(services_data, list):
                    logger.info(f"   Services: {len(services_data)} services")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"❌ Error storing discovery results: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def subscribe_to_device_registry_events(self, websocket: ClientWebSocketResponse) -> bool:
        """
        Subscribe to device registry update events
        
        Args:
            websocket: Connected WebSocket client
            
        Returns:
            True if subscription successful
        """
        try:
            message_id = await self._get_next_id()
            logger.info("📱 Subscribing to device registry update events...")

            await websocket.send_json({
                "id": message_id,
                "type": "subscribe_events",
                "event_type": "device_registry_updated"
            })

            # Wait for subscription confirmation
            response = await self._wait_for_response(websocket, message_id, timeout=5.0)

            if response and response.get("success"):
                logger.info("✅ Subscribed to device registry events")
                return True
            else:
                logger.error("❌ Failed to subscribe to device registry events")
                return False

        except Exception as e:
            logger.error(f"❌ Error subscribing to device registry events: {e}")
            return False

    async def subscribe_to_entity_registry_events(self, websocket: ClientWebSocketResponse) -> bool:
        """
        Subscribe to entity registry update events
        
        Args:
            websocket: Connected WebSocket client
            
        Returns:
            True if subscription successful
        """
        try:
            message_id = await self._get_next_id()
            logger.info("🔌 Subscribing to entity registry update events...")

            await websocket.send_json({
                "id": message_id,
                "type": "subscribe_events",
                "event_type": "entity_registry_updated"
            })

            # Wait for subscription confirmation
            response = await self._wait_for_response(websocket, message_id, timeout=5.0)

            if response and response.get("success"):
                logger.info("✅ Subscribed to entity registry events")
                return True
            else:
                logger.error("❌ Failed to subscribe to entity registry events")
                return False

        except Exception as e:
            logger.error(f"❌ Error subscribing to entity registry events: {e}")
            return False

    async def handle_device_registry_event(self, event: dict[str, Any]) -> bool:
        """
        Handle device registry update event
        
        Args:
            event: Event data from Home Assistant
            
        Returns:
            True if handled successfully
        """
        try:
            data = event.get("data", {})
            action = data.get("action", "unknown")
            device_data = data.get("device", {})
            device_id = data.get("device_id", "unknown")

            logger.info("=" * 80)
            logger.info(f"📱 DEVICE REGISTRY EVENT: {action.upper()}")
            logger.info(f"   Device ID: {device_id}")
            if device_data:
                logger.info(f"   Name: {device_data.get('name', 'Unknown')}")
                logger.info(f"   Manufacturer: {device_data.get('manufacturer', 'Unknown')}")
            logger.info("=" * 80)

            # Store update if we have InfluxDB and device data
            if self.influxdb_manager and device_data:
                try:
                    device = Device.from_ha_device(device_data)
                    device.validate()
                    point = device.to_influx_point()
                    await self.influxdb_manager.write_device(point, bucket="home_assistant_events")
                    logger.info("✅ Stored device update in InfluxDB")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to store device update: {e}")

            return True

        except Exception as e:
            logger.error(f"❌ Error handling device registry event: {e}")
            return False

    async def handle_entity_registry_event(self, event: dict[str, Any]) -> bool:
        """
        Handle entity registry update event
        
        Args:
            event: Event data from Home Assistant
            
        Returns:
            True if handled successfully
        """
        try:
            data = event.get("data", {})
            action = data.get("action", "unknown")
            entity_data = data.get("entity", {})
            entity_id = data.get("entity_id", "unknown")

            logger.info("=" * 80)
            logger.info(f"🔌 ENTITY REGISTRY EVENT: {action.upper()}")
            logger.info(f"   Entity ID: {entity_id}")
            if entity_data:
                logger.info(f"   Platform: {entity_data.get('platform', 'Unknown')}")
            logger.info("=" * 80)

            # Store update if we have InfluxDB and entity data
            if self.influxdb_manager and entity_data:
                try:
                    entity = Entity.from_ha_entity(entity_data)
                    entity.validate()
                    point = entity.to_influx_point()
                    await self.influxdb_manager.write_entity(point, bucket="home_assistant_events")
                    logger.info("✅ Stored entity update in InfluxDB")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to store entity update: {e}")

            # Epic 23.2: Update mapping caches on entity registry events
            if entity_id and entity_data:
                device_id = entity_data.get("device_id")
                if device_id:
                    self.entity_to_device[entity_id] = device_id

                area_id = entity_data.get("area_id")
                if area_id:
                    self.entity_to_area[entity_id] = area_id

                logger.debug(f"Updated mapping cache for entity {entity_id}")

            return True

        except Exception as e:
            logger.error(f"❌ Error handling entity registry event: {e}")
            return False

    # Epic 23.2: Helper methods for device/area lookup
    def get_device_id(self, entity_id: str) -> str | None:
        """
        Get device_id for an entity
        
        Args:
            entity_id: The entity ID to look up
            
        Returns:
            device_id if found, None otherwise
        """
        # Check if cache is stale and log warning
        self._check_cache_freshness()
        return self.entity_to_device.get(entity_id)

    def get_area_id(self, entity_id: str, device_id: str | None = None) -> str | None:
        """
        Get area_id for an entity or device
        
        Checks in this order:
        1. Entity direct area assignment
        2. Device area assignment (if device_id provided or looked up)
        
        Args:
            entity_id: The entity ID to look up
            device_id: Optional device ID (will be looked up if not provided)
            
        Returns:
            area_id if found, None otherwise
        """
        # Check entity-level area first (direct assignment)
        entity_area = self.entity_to_area.get(entity_id)
        if entity_area:
            return entity_area

        # Fallback to device-level area
        if not device_id:
            device_id = self.get_device_id(entity_id)

        if device_id:
            return self.device_to_area.get(device_id)

        return None

    # Epic 23.5: Helper method for device metadata lookup
    def get_device_metadata(self, device_id: str) -> dict[str, Any] | None:
        """
        Get device metadata (manufacturer, model, sw_version)
        
        Args:
            device_id: The device ID to look up
            
        Returns:
            Device metadata dict if found, None otherwise
        """
        return self.device_metadata.get(device_id)

    def _check_cache_freshness(self):
        """
        Check if cache is stale and log warning if needed.
        
        Cache is considered stale if it's older than TTL and has entries.
        This helps identify when discovery hasn't run recently.
        
        Only logs warning once per interval to avoid log spam.
        """
        if self._cache_timestamp and len(self.entity_to_device) > 0:
            cache_age = time.time() - self._cache_timestamp
            if cache_age > self._cache_ttl_seconds:
                # Only log warning if we haven't warned recently
                current_time = time.time()
                should_warn = (
                    self._last_stale_warning_timestamp is None or
                    (current_time - self._last_stale_warning_timestamp) > self._stale_warning_interval
                )

                if should_warn:
                    logger.warning(
                        f"⚠️ Discovery cache is stale ({cache_age/60:.1f} minutes old, "
                        f"TTL: {self._cache_ttl_seconds/60:.1f} minutes). "
                        f"Consider triggering discovery to refresh device/area mappings."
                    )
                    self._last_stale_warning_timestamp = current_time

    def is_cache_stale(self) -> bool:
        """
        Check if cache is stale.
        
        Returns:
            True if cache is older than TTL, False otherwise
        """
        if not self._cache_timestamp or len(self.entity_to_device) == 0:
            return True  # Empty cache is considered stale
        cache_age = time.time() - self._cache_timestamp
        return cache_age > self._cache_ttl_seconds

    def clear_caches(self):
        """
        Clear all mapping caches.
        
        Useful when discovery fails or needs to be reset.
        """
        self.entity_to_device.clear()
        self.device_to_area.clear()
        self.entity_to_area.clear()
        self.device_metadata.clear()
        self._cache_timestamp = None
        logger.info("🧹 Discovery caches cleared")

    def get_cache_statistics(self) -> dict[str, Any]:
        """
        Get statistics about mapping caches
        
        Returns:
            Dictionary with cache statistics
        """
        cache_age_minutes = None
        if self._cache_timestamp:
            cache_age_minutes = (time.time() - self._cache_timestamp) / 60

        return {
            "entity_to_device_mappings": len(self.entity_to_device),
            "device_to_area_mappings": len(self.device_to_area),
            "entity_to_area_mappings": len(self.entity_to_area),
            "device_metadata_entries": len(self.device_metadata),
            "cache_age_minutes": round(cache_age_minutes, 1) if cache_age_minutes else None,
            "cache_ttl_minutes": self._cache_ttl_seconds / 60,
            "is_stale": self.is_cache_stale()
        }

