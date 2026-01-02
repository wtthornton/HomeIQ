"""
Devices Summary Service

Discovers all devices with details (manufacturer, model, area) for context injection.
Provides device inventory with metadata for AI agent context.
"""

import logging
from collections import defaultdict
from typing import Any

import httpx

from ..clients.data_api_client import DataAPIClient
from ..clients.device_intelligence_client import DeviceIntelligenceClient
from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class DevicesSummaryService:
    """
    Service for generating devices summary with details.

    Provides device inventory with:
    - Device name and ID
    - Manufacturer and model
    - Area/room location
    - Entity counts per device (if available)
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize devices summary service.

        Args:
            settings: Application settings
            context_builder: Context builder for cache access
        """
        self.settings = settings
        self.context_builder = context_builder
        self.ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        )
        self.data_api_client = DataAPIClient(base_url=settings.data_api_url)
        # Phase 1.2: Device Intelligence Client for device relationships/context
        self.device_intelligence_client = DeviceIntelligenceClient(settings)
        # Device Intelligence Service URL (optional - for Zigbee2MQTT data)
        self.device_intelligence_url = settings.device_intelligence_url
        self._cache_key = "devices_summary"
        self._cache_ttl = 1800  # 30 minutes (P1: Increased TTL for static data - devices rarely change)

    async def get_summary(self, skip_truncation: bool = False) -> str:
        """
        Get devices summary with manufacturer, model, and area information.

        Args:
            skip_truncation: If True, skip truncation (for debug display)

        Returns:
            Formatted summary with device details grouped by area

        Raises:
            Exception: If unable to fetch devices
        """
        # Check cache first (only if not skipping truncation, as cache may be truncated)
        if not skip_truncation:
            cached = await self.context_builder._get_cached_value(self._cache_key)
            if cached:
                logger.debug("✅ Using cached devices summary")
                return cached

        try:
            # Fetch devices from Data API (local/cached) - 2025 Optimization: Use local data instead of HA API
            logger.info("📱 Fetching devices from Data API (local/cached)...")
            devices = await self.data_api_client.get_devices(limit=1000)
            logger.info(f"✅ Fetched {len(devices) if devices else 0} devices from Data API")

            if not devices:
                summary = "No devices found"
                await self.context_builder._set_cached_value(
                    self._cache_key, summary, self._cache_ttl
                )
                return summary

            # Fetch areas from Data API (extracted from devices/entities) - 2025 Optimization: Use local data
            try:
                areas = await self.data_api_client.get_areas()
                area_name_map = {
                    area.get("area_id"): area.get("name", area.get("area_id", ""))
                    for area in areas
                    if area.get("area_id")
                }
                logger.debug(f"✅ Extracted {len(area_name_map)} areas from Data API")
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch areas from Data API: {e}")
                # Fallback: Extract from devices
                area_name_map = {
                    device.get("area_id"): device.get("area_id", "").replace("_", " ").title()
                    for device in devices
                    if device.get("area_id")
                }

            # Initialize device capabilities dict (Phase 2.1)
            device_capabilities: dict[str, dict[str, Any]] = {}
            
            # Fetch entities to count entities per device and aggregate capabilities
            try:
                entities = await self.data_api_client.fetch_entities(limit=10000)
                
                # Count entities per device
                device_entity_count: dict[str, int] = defaultdict(int)
                # Phase 2.1: Aggregate device capabilities from entities
                device_capabilities = defaultdict(lambda: {
                    "effects": set(),
                    "color_modes": set(),
                    "presets": set()
                })
                
                for entity in entities:
                    device_id = entity.get("device_id")
                    if device_id:
                        device_entity_count[device_id] += 1
                        
                        # Phase 2.1: Aggregate capabilities from entity attributes
                        attributes = entity.get("attributes", {})
                        if "effect_list" in attributes:
                            effect_list = attributes["effect_list"]
                            if isinstance(effect_list, list):
                                device_capabilities[device_id]["effects"].update(effect_list)
                        if "color_mode" in attributes:
                            color_mode = attributes["color_mode"]
                            if isinstance(color_mode, str):
                                device_capabilities[device_id]["color_modes"].add(color_mode)
                        elif "supported_color_modes" in attributes:
                            color_modes = attributes["supported_color_modes"]
                            if isinstance(color_modes, list):
                                device_capabilities[device_id]["color_modes"].update(color_modes)
                        if "preset_modes" in attributes:
                            preset_modes = attributes["preset_modes"]
                            if isinstance(preset_modes, list):
                                device_capabilities[device_id]["presets"].update(preset_modes)
                        # Phase 2.2: Track device constraints
                        if "max_brightness" in attributes:
                            device_capabilities[device_id]["max_brightness"] = attributes["max_brightness"]
                        if "min_color_temp" in attributes and "max_color_temp" in attributes:
                            device_capabilities[device_id]["color_temp_range"] = (
                                attributes["min_color_temp"], attributes["max_color_temp"]
                            )
                
                logger.debug(f"✅ Counted entities for {len(device_entity_count)} devices")
                logger.debug(f"✅ Aggregated capabilities for {len(device_capabilities)} devices")
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch entity counts: {e}")
                device_entity_count = {}
                device_capabilities = {}

            # Fetch Zigbee2MQTT metadata from device-intelligence-service (if available)
            zigbee_metadata_map: dict[str, dict[str, Any]] = {}
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    # Use the devices API endpoint to get devices with Zigbee data
                    response = await client.get(f"{self.device_intelligence_url}/api/devices?limit=1000")
                    if response.status_code == 200:
                        result = response.json()
                        zigbee_devices = result.get("devices", []) if isinstance(result, dict) else result
                        # Create mapping by device_id
                        for z_device in zigbee_devices:
                            device_id_from_zigbee = z_device.get("device_id")
                            if device_id_from_zigbee:
                                zigbee_metadata_map[device_id_from_zigbee] = {
                                    "lqi": z_device.get("lqi"),
                                    "availability_status": z_device.get("availability_status"),
                                    "battery_level": z_device.get("battery_level"),
                                    "battery_low": z_device.get("battery_low"),
                                }
                        logger.info(f"✅ Fetched Zigbee2MQTT metadata for {len(zigbee_metadata_map)} devices")
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch Zigbee2MQTT metadata (device-intelligence-service may not be available): {e}")
                # Continue without Zigbee metadata - not critical

            # Group devices by area
            devices_by_area: dict[str, list[dict[str, Any]]] = defaultdict(list)
            unassigned_devices: list[dict[str, Any]] = []

            logger.info(f"📱 Processing {len(devices)} devices for grouping")
            devices_processed = 0
            devices_skipped_no_id = 0
            devices_with_area = 0
            devices_without_area = 0
            
            # Debug: Check first device structure
            if devices:
                first_device_keys = list(devices[0].keys())
                logger.info(f"📱 First device keys: {first_device_keys}")
                logger.info(f"📱 First device sample: device_id={devices[0].get('device_id')}, area_id={devices[0].get('area_id')}, name={devices[0].get('name')}")
            
            for device in devices:
                device_id = device.get("device_id")
                if not device_id:
                    devices_skipped_no_id += 1
                    logger.debug(f"⚠️ Skipping device (no device_id): {device}")
                    continue

                # Get device metadata
                device_name = device.get("name", device_id)
                manufacturer = device.get("manufacturer") or "Unknown"
                model = device.get("model") or "Unknown"
                area_id = device.get("area_id")
                # Prefer entity_count from device response, fallback to manual count
                entity_count = device.get("entity_count") or device_entity_count.get(device_id, 0)
                
                # Phase 1.1: Get device health score (if available)
                health_score = device.get("health_score")
                
                # Phase 1.2: Get device description/relationships (if available)
                device_description = device.get("device_description")
                device_type = device.get("device_type")
                
                # Phase 1.2: Fetch device context from Device Intelligence Service if description missing
                if not device_description and self.device_intelligence_client.enabled:
                    try:
                        device_payload = {
                            "device_id": device_id,
                            "manufacturer": manufacturer,
                            "model": model,
                            "name": device_name,
                            "area_id": area_id
                        }
                        # Get device entities for context
                        device_entities = [e for e in entities if e.get("device_id") == device_id]
                        context_result = await self.device_intelligence_client.get_device_context(
                            device_id, device_payload, device_entities[:10]  # Limit to 10 entities
                        )
                        if context_result and context_result.get("context"):
                            context = context_result["context"]
                            # Extract device_description from context if available
                            if isinstance(context, dict):
                                device_description = context.get("device_description") or context.get("description")
                            elif isinstance(context, str):
                                # If context is a string, use it as description
                                device_description = context
                    except Exception as e:
                        logger.debug(f"⚠️ Could not fetch device context for {device_id}: {e}")
                        # Continue without device description - not critical
                
                # Phase 2.4: Get energy consumption data from device (if available)
                power_w = device.get("power_consumption_active_w")
                daily_kwh = None
                if power_w:
                    # Estimate daily kWh (power_w * 24h / 1000)
                    daily_kwh = round((power_w * 24) / 1000, 2)

                device_info = {
                    "device_id": device_id,
                    "name": device_name,
                    "manufacturer": manufacturer,
                    "model": model,
                    "area_id": area_id,
                    "entity_count": entity_count,
                    "disabled_by": device.get("disabled_by"),
                    "sw_version": device.get("sw_version"),
                    "hw_version": device.get("hw_version"),
                    # Phase 1.1: Health score
                    "health_score": health_score,
                    # Phase 1.2: Device relationships
                    "device_description": device_description,
                    "device_type": device_type,
                    # Zigbee2MQTT fields (will be populated if available)
                    "zigbee_ieee": None,
                    "lqi": None,
                    "availability_status": None,
                    "battery_level": None,
                    "battery_low": None,
                }

                # Enhance with Zigbee2MQTT metadata if available
                # Try matching by device_id first, then by IEEE address
                zigbee_meta = zigbee_metadata_map.get(device_id)
                if not zigbee_meta:
                    # Try matching by IEEE address if available in device identifiers
                    # This would require checking device connections/identifiers
                    pass
                
                if zigbee_meta:
                    device_info.update(zigbee_meta)

                if area_id:
                    devices_by_area[area_id].append(device_info)
                    devices_with_area += 1
                else:
                    unassigned_devices.append(device_info)
                    devices_without_area += 1
                
                devices_processed += 1

            logger.info(f"📱 Grouped devices: {devices_processed} processed, {devices_skipped_no_id} skipped (no device_id), {devices_with_area} with area, {devices_without_area} without area, {len(devices_by_area)} areas with devices, {len(unassigned_devices)} unassigned")
            
            # Format devices by area
            summary_parts = []

            # Sort areas by name
            sorted_areas = sorted(
                devices_by_area.keys(),
                key=lambda a: area_name_map.get(a, a).lower()
            )
            
            logger.info(f"📱 Formatting summary: {len(sorted_areas)} areas, {len(unassigned_devices)} unassigned devices, area_name_map has {len(area_name_map)} entries")

            # Format devices in each area
            logger.info(f"📱 Starting to format {len(sorted_areas)} areas")
            for area_id in sorted_areas:
                try:
                    area_name = area_name_map.get(area_id, area_id.replace("_", " ").title())
                    area_devices = devices_by_area[area_id]
                    logger.debug(f"📱 Formatting area {area_id} ({area_name}): {len(area_devices)} devices")

                    # Sort devices by name
                    area_devices.sort(key=lambda d: d["name"].lower())

                    area_parts = [f"{area_name} ({len(area_devices)} devices):"]
                    
                    # Limit devices per area for token efficiency (unless skipping truncation)
                    device_limit = len(area_devices) if skip_truncation else min(20, len(area_devices))
                    
                    for device in area_devices[:device_limit]:
                        # Format: "Device Name (manufacturer model) [X entities]"
                        device_line_parts = [device["name"]]
                        
                        # Add manufacturer/model if available
                        if device["manufacturer"] != "Unknown" or device["model"] != "Unknown":
                            manufacturer_model = f"{device['manufacturer']} {device['model']}".strip()
                            if manufacturer_model and manufacturer_model != "Unknown Unknown":
                                device_line_parts.append(f"({manufacturer_model})")
                        
                        # Add entity count if available
                        if device["entity_count"] > 0:
                            device_line_parts.append(f"[{device['entity_count']} entities]")
                        
                        # Phase 1.1: Add health score if available
                        if device.get("health_score") is not None:
                            health_score = device["health_score"]
                            # Highlight low health scores (< 70) as recommended in system prompt
                            if health_score < 70:
                                device_line_parts.append(f"[⚠️ health_score: {health_score}]")
                            else:
                                device_line_parts.append(f"[health_score: {health_score}]")
                        
                        # Phase 1.2: Add device description/relationships if available
                        if device.get("device_description"):
                            device_line_parts.append(f"[{device['device_description']}]")
                        
                        # Phase 2.1: Add device capabilities summary if available
                        device_id_for_caps = device["device_id"]
                        if device_id_for_caps in device_capabilities:
                            caps = device_capabilities[device_id_for_caps]
                            caps_parts = []
                            if caps.get("effects"):
                                effects_list = list(caps["effects"])[:3]  # Show top 3 effects
                                caps_parts.append(f"effects: {', '.join(effects_list)}")
                            if caps.get("color_modes"):
                                color_modes_list = list(caps["color_modes"])[:2]  # Show top 2 color modes
                                caps_parts.append(f"colors: {', '.join(color_modes_list)}")
                            if caps.get("presets"):
                                presets_list = list(caps["presets"])[:3]  # Show top 3 presets
                                caps_parts.append(f"presets: {', '.join(presets_list)}")
                            # Phase 2.2: Add device constraints
                            if "max_brightness" in caps:
                                caps_parts.append(f"max_brightness: {caps['max_brightness']}")
                            if "color_temp_range" in caps:
                                min_temp, max_temp = caps["color_temp_range"]
                                caps_parts.append(f"color_temp: {min_temp}-{max_temp}")
                            
                            if caps_parts:
                                device_line_parts.append(f"[{', '.join(caps_parts)}]")
                        
                        # Phase 2.4: Add energy consumption data if available
                        power_w = device.get("power_consumption_active_w")
                        daily_kwh = device.get("daily_kwh")
                        if power_w:
                            energy_parts = [f"power: {power_w}W"]
                            if daily_kwh:
                                energy_parts.append(f"daily: {daily_kwh}kWh")
                            else:
                                # Estimate daily kWh
                                estimated_daily = round((power_w * 24) / 1000, 2)
                                energy_parts.append(f"daily: ~{estimated_daily}kWh")
                            device_line_parts.append(f"[{', '.join(energy_parts)}]")
                        
                        # Add Zigbee2MQTT information if available
                        zigbee_info_parts = []
                        if device.get("lqi") is not None:
                            zigbee_info_parts.append(f"LQI: {device['lqi']}")
                        if device.get("availability_status"):
                            status = device["availability_status"]
                            if status != "enabled":
                                zigbee_info_parts.append(f"Status: {status}")
                        if device.get("battery_level") is not None:
                            zigbee_info_parts.append(f"Battery: {device['battery_level']}%")
                        if device.get("battery_low"):
                            zigbee_info_parts.append("Battery Low")
                        
                        if zigbee_info_parts:
                            device_line_parts.append(f"[{', '.join(zigbee_info_parts)}]")
                        
                        # Add device_id for reference
                        device_line_parts.append(f"[id: {device['device_id']}]")
                        
                        area_parts.append(f"  - {' '.join(device_line_parts)}")
                    
                    if not skip_truncation and len(area_devices) > 20:
                        area_parts.append(f"  ... and {len(area_devices) - 20} more devices")
                    
                    summary_parts.append("\n".join(area_parts))
                    logger.debug(f"📱 Added area {area_id} to summary ({len(area_parts)} lines)")
                except Exception as e:
                    logger.error(f"❌ Error formatting area {area_id}: {e}", exc_info=True)

            # Add unassigned devices
            if unassigned_devices:
                unassigned_devices.sort(key=lambda d: d["name"].lower())
                unassigned_limit = len(unassigned_devices) if skip_truncation else min(20, len(unassigned_devices))
                
                unassigned_parts = [f"Unassigned ({len(unassigned_devices)} devices):"]
                for device in unassigned_devices[:unassigned_limit]:
                    device_line_parts = [device["name"]]
                    
                    if device["manufacturer"] != "Unknown" or device["model"] != "Unknown":
                        manufacturer_model = f"{device['manufacturer']} {device['model']}".strip()
                        if manufacturer_model and manufacturer_model != "Unknown Unknown":
                            device_line_parts.append(f"({manufacturer_model})")
                    
                    if device["entity_count"] > 0:
                        device_line_parts.append(f"[{device['entity_count']} entities]")
                    
                    # Phase 1.1: Add health score if available
                    if device.get("health_score") is not None:
                        health_score = device["health_score"]
                        # Highlight low health scores (< 70) as recommended in system prompt
                        if health_score < 70:
                            device_line_parts.append(f"[⚠️ health_score: {health_score}]")
                        else:
                            device_line_parts.append(f"[health_score: {health_score}]")
                    
                    # Phase 1.2: Add device description/relationships if available
                    if device.get("device_description"):
                        device_line_parts.append(f"[{device['device_description']}]")
                    
                    # Phase 2.1: Add device capabilities summary if available
                    device_id_for_caps = device["device_id"]
                    if device_id_for_caps in device_capabilities:
                        caps = device_capabilities[device_id_for_caps]
                        caps_parts = []
                        if caps.get("effects"):
                            effects_list = list(caps["effects"])[:3]  # Show top 3 effects
                            caps_parts.append(f"effects: {', '.join(effects_list)}")
                        if caps.get("color_modes"):
                            color_modes_list = list(caps["color_modes"])[:2]  # Show top 2 color modes
                            caps_parts.append(f"colors: {', '.join(color_modes_list)}")
                        if caps.get("presets"):
                            presets_list = list(caps["presets"])[:3]  # Show top 3 presets
                            caps_parts.append(f"presets: {', '.join(presets_list)}")
                        # Phase 2.2: Add device constraints
                        if "max_brightness" in caps:
                            caps_parts.append(f"max_brightness: {caps['max_brightness']}")
                        if "color_temp_range" in caps:
                            min_temp, max_temp = caps["color_temp_range"]
                            caps_parts.append(f"color_temp: {min_temp}-{max_temp}")
                        
                        if caps_parts:
                            device_line_parts.append(f"[{', '.join(caps_parts)}]")
                    
                    # Phase 2.4: Add energy consumption data if available
                    power_w = device.get("power_consumption_active_w")
                    daily_kwh = device.get("daily_kwh")
                    if power_w:
                        energy_parts = [f"power: {power_w}W"]
                        if daily_kwh:
                            energy_parts.append(f"daily: {daily_kwh}kWh")
                        else:
                            # Estimate daily kWh
                            estimated_daily = round((power_w * 24) / 1000, 2)
                            energy_parts.append(f"daily: ~{estimated_daily}kWh")
                        device_line_parts.append(f"[{', '.join(energy_parts)}]")
                    
                    # Add Zigbee2MQTT information if available
                    zigbee_info_parts = []
                    if device.get("lqi") is not None:
                        zigbee_info_parts.append(f"LQI: {device['lqi']}")
                    if device.get("availability_status"):
                        status = device["availability_status"]
                        if status != "enabled":
                            zigbee_info_parts.append(f"Status: {status}")
                    if device.get("battery_level") is not None:
                        zigbee_info_parts.append(f"Battery: {device['battery_level']}%")
                    if device.get("battery_low"):
                        zigbee_info_parts.append("Battery Low")
                    
                    if zigbee_info_parts:
                        device_line_parts.append(f"[{', '.join(zigbee_info_parts)}]")
                    
                    device_line_parts.append(f"[id: {device['device_id']}]")
                    unassigned_parts.append(f"  - {' '.join(device_line_parts)}")
                
                if not skip_truncation and len(unassigned_devices) > 20:
                    unassigned_parts.append(f"  ... and {len(unassigned_devices) - 20} more devices")
                
                summary_parts.append("\n".join(unassigned_parts))

            summary = "\n\n".join(summary_parts)
            
            logger.info(f"📱 Summary built: {len(summary_parts)} parts, {len(summary)} chars")

            # Truncate if too long (optimized: max 4000 chars for token efficiency)
            # Skip truncation for debug display
            if not skip_truncation and len(summary) > 4000:
                summary = summary[:4000] + "\n... (truncated)"
                logger.info(f"📱 Summary truncated to 4000 chars")

            # Cache the result (only if not skipping truncation)
            if not skip_truncation:
                await self.context_builder._set_cached_value(
                    self._cache_key, summary, self._cache_ttl
                )

            total_devices = len(devices)
            logger.info(f"✅ Generated devices summary: {total_devices} devices across {len(sorted_areas)} areas ({len(summary)} chars)")
            return summary

        except Exception as e:
            logger.error(f"❌ Error generating devices summary: {e}", exc_info=True)
            # Return fallback
            return "Devices unavailable. Please check Home Assistant connection."

    async def close(self):
        """Close service resources"""
        await self.ha_client.close()
        await self.data_api_client.close()

