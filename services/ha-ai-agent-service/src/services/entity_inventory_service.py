"""
Entity Inventory Summary Service

Aggregates entity counts by domain and area for context injection.
Epic AI-19: Story AI19.2
Enhanced: Added friendly names, device_ids, aliases, labels, states, and device metadata
"""

import logging
from collections import defaultdict
from typing import Any

from ..clients.data_api_client import DataAPIClient
from ..clients.device_intelligence_client import DeviceIntelligenceClient
from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class EntityInventoryService:
    """
    Service for generating entity inventory summaries.

    Aggregates entity counts by domain and area with enhanced metadata:
    - Entity friendly names for automation descriptions
    - Device IDs for target.device_id usage
    - Entity aliases for entity resolution (2025 feature)
    - Entity labels for organizational filtering
    - Current states for context
    - Device metadata (manufacturer, model)
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize entity inventory service.

        Args:
            settings: Application settings
            context_builder: Context builder for cache access
        """
        self.settings = settings
        self.context_builder = context_builder
        self.data_api_client = DataAPIClient(base_url=settings.data_api_url)
        self.ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        )
        self.device_intelligence_client = DeviceIntelligenceClient(settings)
        self._cache_key = "entity_inventory_summary"
        self._cache_ttl = 300  # 5 minutes
    
    async def _get_device_mapping_info(
        self,
        device_id: str,
        device_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Get device mapping information from Device Intelligence Service.
        
        Args:
            device_id: Device ID
            device_data: Device data dictionary
            
        Returns:
            Dictionary with device type, relationships, and context, or None if unavailable
        """
        try:
            # Prepare device data for API call
            device_payload = {
                "device_id": device_id,
                "manufacturer": device_data.get("manufacturer"),
                "model": device_data.get("model"),
                "name": device_data.get("name"),
                "area_id": device_data.get("area_id")
            }
            
            # Get device type
            type_result = await self.device_intelligence_client.get_device_type(
                device_id, device_payload
            )
            
            if not type_result:
                return None
            
            # Get device context
            context_result = await self.device_intelligence_client.get_device_context(
                device_id, device_payload
            )
            
            # Combine results
            result = {
                "type": type_result.get("type"),
                "handler": type_result.get("handler"),
                "context": context_result.get("context") if context_result else None
            }
            
            # Get relationships if available
            relationships_result = await self.device_intelligence_client.get_device_relationships(
                device_id, device_payload
            )
            if relationships_result:
                result["relationships"] = relationships_result.get("relationships", [])
            
            return result
        except Exception as e:
            logger.debug(f"⚠️ Error getting device mapping info for {device_id}: {e}")
            return None

    async def get_summary(self) -> str:
        """
        Get enhanced entity inventory summary with friendly names, device IDs, aliases, labels, and states.

        Returns:
            Formatted summary with entity counts, friendly names, device IDs, and key metadata

        Raises:
            Exception: If unable to fetch or process entities
        """
        # Check cache first
        cached = await self.context_builder._get_cached_value(self._cache_key)
        if cached:
            logger.debug("✅ Using cached entity inventory summary")
            return cached

        try:
            # Fetch all entities from data-api
            logger.info("📊 Fetching entities for inventory summary...")
            entities = await self.data_api_client.fetch_entities(limit=10000)

            if not entities:
                summary = "No entities found in system."
                await self.context_builder._set_cached_value(
                    self._cache_key, summary, self._cache_ttl
                )
                return summary

            # Fetch entity states for current state information
            logger.info("📊 Fetching entity states...")
            try:
                states = await self.ha_client.get_states()
                state_map = {state.get("entity_id"): state for state in states}
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch states: {e}")
                state_map = {}

            # Fetch areas for friendly name mapping
            try:
                areas = await self.ha_client.get_area_registry()
                area_name_map = {
                    area.get("area_id"): area.get("name", area.get("area_id", ""))
                    for area in areas
                    if area.get("area_id")
                }
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch areas: {e}")
                area_name_map = {}

            # Fetch Device Registry for area resolution and metadata (Epic AI-23)
            device_area_map: dict[str, str] = {}  # device_id → area_id
            device_metadata_map: dict[str, dict[str, Any]] = {}  # device_id → device_data
            try:
                logger.info("📊 Fetching device registry for area resolution...")
                devices = await self.ha_client.get_device_registry()
                for device in devices:
                    device_id = device.get("id")
                    if device_id:
                        # Create device_id → area_id mapping
                        device_area_id = device.get("area_id")
                        if device_area_id:
                            device_area_map[device_id] = device_area_id
                        # Store device metadata (manufacturer, model, etc.)
                        device_metadata_map[device_id] = {
                            "manufacturer": device.get("manufacturer"),
                            "model": device.get("model"),
                            "sw_version": device.get("sw_version"),
                            "hw_version": device.get("hw_version"),
                            "name": device.get("name"),
                            "disabled_by": device.get("disabled_by")
                        }
                logger.info(f"✅ Mapped {len(device_area_map)} devices with areas, {len(device_metadata_map)} devices with metadata")
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch device registry: {e}")
                # Continue without device registry (backward compatible)

            # Device Type Detection (Epic AI-24: Use Device Mapping Library)
            # Cache for device mapping results to avoid excessive API calls
            device_mapping_cache: dict[str, dict[str, Any]] = {}  # device_id → mapping results
            
            # Fallback: Legacy device type detection (Epic AI-23 Story AI23.3) - kept for backward compatibility
            hue_room_devices: dict[str, dict[str, Any]] = {}  # device_id → device_data (Hue Room/Zone groups)
            wled_master_entities: dict[str, str] = {}  # entity_id → master_entity_id (for segments)
            device_relationships: dict[str, list[str]] = {}  # device_id/entity_id → related entities
            
            # Try to use device mapping library for device type detection
            # Process devices in batches to improve performance
            device_ids_to_process = list(device_metadata_map.keys())
            logger.info(f"🔍 Processing {len(device_ids_to_process)} devices with device mapping library...")
            
            # Process devices (with fallback to legacy detection)
            for device_id, device_data in device_metadata_map.items():
                # Try device mapping library first (Epic AI-24)
                device_mapping_result = await self._get_device_mapping_info(device_id, device_data)
                if device_mapping_result:
                    device_mapping_cache[device_id] = device_mapping_result
                    logger.debug(f"✅ Device mapping library detected device type for {device_id}: {device_mapping_result.get('type')}")
                else:
                    # Fallback to legacy detection (Epic AI-23)
                    model = (device_data.get("model") or "").lower()
                    manufacturer = (device_data.get("manufacturer") or "").lower()
                    
                    # Detect Hue Room/Zone groups (legacy)
                    if ("room" in model or "zone" in model) and ("signify" in manufacturer or "philips" in manufacturer):
                        hue_room_devices[device_id] = device_data
                        logger.debug(f"✅ Legacy detection: Hue Room/Zone group: {device_id}")
            
            # Detect WLED segments (legacy fallback)
            for entity in entities:
                entity_id = entity.get("entity_id", "")
                if "_segment_" in entity_id.lower():
                    base_name = entity_id.split("_segment_")[0]
                    wled_master_entities[entity_id] = base_name
                    logger.debug(f"✅ Legacy detection: WLED segment: {entity_id}")
            
            # Build device relationships from device mapping library or legacy
            for device_id in device_metadata_map.keys():
                if device_id in device_mapping_cache:
                    # Use relationships from device mapping library
                    mapping_result = device_mapping_cache[device_id]
                    relationships = mapping_result.get("relationships", [])
                    if relationships:
                        device_relationships[device_id] = [
                            rel.get("device_id") or rel.get("entity_id", "")
                            for rel in relationships
                            if rel.get("device_id") or rel.get("entity_id")
                        ]
                else:
                    # Legacy: Link individual lights to Hue Room groups
                    if device_id in hue_room_devices:
                        for entity in entities:
                            entity_device_id = entity.get("device_id")
                            if entity_device_id == device_id:
                                if device_id not in device_relationships:
                                    device_relationships[device_id] = []
                                device_relationships[device_id].append(entity.get("entity_id", ""))

            # Fetch Entity Registry for aliases and metadata (Epic AI-23)
            entity_registry_map: dict[str, dict[str, Any]] = {}  # entity_id → entity_registry_data
            try:
                logger.info("📊 Fetching entity registry for aliases and metadata...")
                entity_registry = await self.ha_client.get_entity_registry()
                for entity_reg in entity_registry:
                    entity_id = entity_reg.get("entity_id")
                    if entity_id:
                        entity_registry_map[entity_id] = {
                            "aliases": entity_reg.get("aliases", []),
                            "category": entity_reg.get("category"),
                            "disabled_by": entity_reg.get("disabled_by"),
                            "hidden_by": entity_reg.get("hidden_by"),
                            "labels": entity_reg.get("labels", []),
                            "name": entity_reg.get("name"),
                            "original_name": entity_reg.get("original_name")
                        }
                logger.info(f"✅ Mapped {len(entity_registry_map)} entities with registry data")
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch entity registry: {e}")
                # Continue without entity registry (backward compatible)

            # Aggregate by domain and area
            domain_area_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
            domain_totals: dict[str, int] = defaultdict(int)

            # Sample entities per domain for detailed examples (optimized: show unique patterns)
            domain_samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
            # Track unique patterns for lights (by manufacturer/type)
            light_patterns: dict[str, dict[str, Any]] = {}

            for entity in entities:
                # Skip None entities (defensive programming)
                if entity is None:
                    continue
                    
                domain = entity.get("domain", "unknown")
                
                # CRITICAL FIX (Epic AI-23): Resolve area_id from device if entity doesn't have it
                entity_area_id = entity.get("area_id")
                entity_device_id = entity.get("device_id")
                
                # If entity doesn't have area_id, try to get it from device
                if not entity_area_id and entity_device_id:
                    entity_area_id = device_area_map.get(entity_device_id)
                    if entity_area_id:
                        logger.debug(f"✅ Resolved area_id for {entity.get('entity_id')} from device {entity_device_id}: {entity_area_id}")
                
                area_id = entity_area_id or "unassigned"
                domain_area_counts[domain][area_id] += 1
                domain_totals[domain] += 1
                
                # Get device metadata for entity (Epic AI-23)
                device_metadata = device_metadata_map.get(entity_device_id, {}) if entity_device_id else {}
                # Merge device metadata into entity data
                if device_metadata:
                    entity["manufacturer"] = entity.get("manufacturer") or device_metadata.get("manufacturer")
                    entity["model"] = entity.get("model") or device_metadata.get("model")

                # Get entity registry data for this entity (Epic AI-23)
                entity_id = entity.get("entity_id", "")
                entity_reg_data = entity_registry_map.get(entity_id, {})
                entity_aliases = entity_reg_data.get("aliases", [])
                entity_category = entity_reg_data.get("category")
                entity_disabled = entity_reg_data.get("disabled_by") is not None

                # For lights: collect unique patterns (one per manufacturer/type)
                if domain == "light":
                    entity_state = state_map.get(entity_id, {})
                    entity_attributes = entity_state.get("attributes", {})
                    # Use device metadata if available (Epic AI-23)
                    manufacturer = entity.get("manufacturer") or device_metadata.get("manufacturer") or "unknown"
                    model = entity.get("model") or device_metadata.get("model") or ""
                    pattern_key = f"{manufacturer}_{model}".lower()
                    
                    # Device type detection (Epic AI-24: Use Device Mapping Library)
                    device_type = None
                    device_description = None
                    entity_device_id = entity.get("device_id")
                    
                    # Try device mapping library first
                    if entity_device_id and entity_device_id in device_mapping_cache:
                        mapping_result = device_mapping_cache[entity_device_id]
                        device_type_result = mapping_result.get("type")
                        context_result = mapping_result.get("context")
                        
                        if device_type_result:
                            device_type = device_type_result
                        if context_result:
                            device_description = context_result
                    # Fallback to legacy detection
                    elif entity_device_id and entity_device_id in hue_room_devices:
                        device_type = "hue_room"
                        related_lights = device_relationships.get(entity_device_id, [])
                        device_description = f"Hue Room - controls {len(related_lights)} lights"
                    elif entity_id in wled_master_entities:
                        device_type = "wled_segment"
                        master_base = wled_master_entities[entity_id]
                        device_description = f"WLED segment (master: {master_base})"
                    elif "wled" in entity_id.lower() and entity_id not in wled_master_entities:
                        device_type = "wled_master"
                        device_description = "WLED master - controls entire strip"
                    
                    # Only add if we don't have this pattern yet (max 8 unique patterns)
                    if pattern_key not in light_patterns and len(light_patterns) < 8:
                        friendly_name = entity.get("friendly_name") or entity.get("name") or entity_id.split(".", 1)[1] if "." in entity_id else entity_id
                        light_patterns[pattern_key] = {
                            "entity_id": entity_id,
                            "friendly_name": friendly_name,
                            "area_id": area_id,
                            "effect_list": entity_attributes.get("effect_list", []),
                            "preset_list": entity_attributes.get("preset_list", []),
                            "theme_list": entity_attributes.get("theme_list", []),
                            "supported_color_modes": entity_attributes.get("supported_color_modes", []),
                            "manufacturer": manufacturer,
                            "model": model,
                            "aliases": entity_aliases,  # Epic AI-23: Include aliases
                            "category": entity_category,  # Epic AI-23: Include category
                            "device_type": device_type,  # Epic AI-23 Story AI23.3: Device type
                            "device_description": device_description  # Epic AI-23 Story AI23.3: Device description
                        }
                # For other domains: collect samples (max 3 per domain)
                elif domain in ["switch", "sensor", "climate", "cover", "lock", "fan"]:
                    if len(domain_samples[domain]) < 3:
                        friendly_name = entity.get("friendly_name") or entity.get("name") or entity_id.split(".", 1)[1] if "." in entity_id else entity_id
                        # Include device metadata and entity registry data in samples (Epic AI-23)
                        sample_data = {
                            "entity_id": entity_id,
                            "friendly_name": friendly_name,
                            "area_id": area_id
                        }
                        if device_metadata.get("manufacturer"):
                            sample_data["manufacturer"] = device_metadata.get("manufacturer")
                        if device_metadata.get("model"):
                            sample_data["model"] = device_metadata.get("model")
                        if entity_aliases:
                            sample_data["aliases"] = entity_aliases  # Epic AI-23: Include aliases
                        if entity_category:
                            sample_data["category"] = entity_category  # Epic AI-23: Include category
                        domain_samples[domain].append(sample_data)

            # Format summary with enhanced information
            summary_parts = []
            for domain in sorted(domain_totals.keys()):
                total = domain_totals[domain]
                area_counts = domain_area_counts[domain]

                # Format area breakdown with friendly names
                area_parts = []
                for area_id in sorted(area_counts.keys()):
                    count = area_counts[area_id]
                    area_name = area_name_map.get(area_id, area_id.replace("_", " ").title() if area_id != "unassigned" else "unassigned")
                    area_parts.append(f"{area_name}: {count}")

                area_str = ", ".join(area_parts)
                domain_display = domain.replace("_", " ").title()

                # Build domain summary line
                domain_line = f"{domain_display}: {total} entities ({area_str})"

                # Add sample entity details for key domains (optimized format)
                if domain in ["light", "switch", "sensor", "climate", "cover", "lock", "fan"]:
                    if domain == "light":
                        # Show unique light patterns (5-8 examples)
                        samples = list(light_patterns.values())[:8]
                        sample_parts = []
                        for sample in samples:
                            # Format: friendly_name (entity_id)
                            sample_info = f"{sample['friendly_name']} ({sample['entity_id']})"
                            
                            # Add device type description if available (Epic AI-23 Story AI23.3)
                            device_description = sample.get("device_description")
                            if device_description:
                                sample_info = f"{sample['friendly_name']} ({sample['entity_id']}) - {device_description}"
                            
                            # Add aliases if available (Epic AI-23)
                            aliases = sample.get("aliases", [])
                            if aliases:
                                alias_preview = ", ".join(aliases[:3])  # Show 3 aliases max
                                if len(aliases) > 3:
                                    sample_info += f", aliases: [{alias_preview}, ...]"
                                else:
                                    sample_info += f", aliases: [{alias_preview}]"
                            
                            # Add effect_list with count + examples (optimized)
                            effect_list = sample.get("effect_list", [])
                            if effect_list:
                                effect_count = len(effect_list)
                                effect_preview = ", ".join(effect_list[:5])  # Show 5 examples max
                                if effect_count > 5:
                                    sample_info += f", effects: {effect_count} [{effect_preview}, ...]"
                                else:
                                    sample_info += f", effects: [{effect_preview}]"
                            
                            # Add preset_list with count + examples
                            preset_list = sample.get("preset_list", [])
                            if preset_list:
                                preset_count = len(preset_list)
                                preset_preview = ", ".join(preset_list[:3])  # Show 3 examples max
                                if preset_count > 3:
                                    sample_info += f", presets: {preset_count} [{preset_preview}, ...]"
                                else:
                                    sample_info += f", presets: [{preset_preview}]"
                            
                            # Add theme_list with count + examples
                            theme_list = sample.get("theme_list", [])
                            if theme_list:
                                theme_count = len(theme_list)
                                theme_preview = ", ".join(theme_list[:3])  # Show 3 examples max
                                if theme_count > 3:
                                    sample_info += f", themes: {theme_count} [{theme_preview}, ...]"
                                else:
                                    sample_info += f", themes: [{theme_preview}]"
                            
                            # Add color modes (concise)
                            color_modes = sample.get("supported_color_modes", [])
                            if color_modes:
                                sample_info += f", colors: {', '.join(color_modes)}"
                            
                            sample_parts.append(sample_info)
                    else:
                        # For other domains: include aliases if available (Epic AI-23)
                        samples = domain_samples[domain][:3] if domain_samples.get(domain) else []
                        sample_parts = []
                        for s in samples:
                            sample_str = f"{s['friendly_name']} ({s['entity_id']})"
                            # Add aliases if available
                            aliases = s.get("aliases", [])
                            if aliases:
                                alias_preview = ", ".join(aliases[:2])  # Show 2 aliases max
                                if len(aliases) > 2:
                                    sample_str += f" [aliases: {alias_preview}, ...]"
                                else:
                                    sample_str += f" [aliases: {alias_preview}]"
                            sample_parts.append(sample_str)
                    
                    if sample_parts:
                        domain_line += f"\n  Examples: {', '.join(sample_parts)}"

                summary_parts.append(domain_line)

            summary = "\n".join(summary_parts)

            # Truncate if too long (optimized: max 2000 chars for token efficiency)
            if len(summary) > 2000:
                summary = summary[:2000] + "... (truncated)"

            # Cache the result
            await self.context_builder._set_cached_value(
                self._cache_key, summary, self._cache_ttl
            )

            logger.info(f"✅ Generated optimized entity inventory summary ({len(summary)} chars, ~{len(summary)//4} tokens)")
            return summary

        except Exception as e:
            logger.error(f"❌ Error generating entity inventory summary: {e}", exc_info=True)
            # Return fallback summary
            return "Entity inventory unavailable. Please check data-api service."

    async def close(self):
        """Close service resources"""
        await self.data_api_client.close()
        await self.ha_client.close()

