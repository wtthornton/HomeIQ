"""
Enhanced Context Builder Service

Provides area-focused entity context for automation creation.
Addresses gaps in standard context that prevent accurate YAML generation.

Key Improvements:
1. Entity IDs grouped by area (for target.area_id and entity resolution)
2. Binary sensors (motion/presence) explicitly listed
3. Trigger platform documentation
4. Existing automations (for duplicate detection)
5. Area-filtered entity lists
"""

import logging
from collections import defaultdict
from typing import Any

from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient
from ..config import Settings

logger = logging.getLogger(__name__)


class EnhancedContextBuilder:
    """
    Builds enhanced context with area-focused entity information.
    
    Supplements the standard context with:
    - Area-to-entity mappings (entity_ids by area)
    - Binary sensors (motion, presence, occupancy)
    - Existing automations (for duplicate detection)
    - Trigger platform reference
    """
    
    def __init__(self, settings: Settings):
        """Initialize enhanced context builder."""
        self.settings = settings
        self.ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        )
        self.data_api_client = DataAPIClient(base_url=settings.data_api_url)
    
    async def close(self):
        """Close client connections."""
        await self.ha_client.close()
        await self.data_api_client.close()
    
    async def build_area_entity_context(self, area_ids: list[str] | None = None) -> str:
        """
        Build entity context grouped by area.
        
        Args:
            area_ids: Optional list of area IDs to filter. If None, includes all areas.
            
        Returns:
            Formatted context string with entities grouped by area
        """
        try:
            # Fetch entities
            entities = await self.data_api_client.fetch_entities(limit=10000)
            if not entities:
                return "ENTITY_INVENTORY: No entities found"
            
            # Fetch device registry for area resolution
            devices = await self.ha_client.get_device_registry()
            device_area_map = {
                d.get("id"): d.get("area_id")
                for d in devices if d.get("id") and d.get("area_id")
            }
            
            # Fetch areas for friendly names
            areas = await self.ha_client.get_area_registry()
            area_name_map = {
                a.get("area_id"): a.get("name", a.get("area_id", ""))
                for a in areas if a.get("area_id")
            }
            
            # Group entities by area and domain
            area_domain_entities: dict[str, dict[str, list[dict]]] = defaultdict(
                lambda: defaultdict(list)
            )
            
            for entity in entities:
                entity_id = entity.get("entity_id", "")
                domain = entity.get("domain", "unknown")
                
                # Resolve area_id (from entity or device)
                area_id = entity.get("area_id")
                if not area_id:
                    device_id = entity.get("device_id")
                    if device_id:
                        area_id = device_area_map.get(device_id)
                
                area_id = area_id or "unassigned"
                
                # Filter by area_ids if specified
                if area_ids and area_id not in area_ids:
                    continue
                
                # Get friendly name and state
                friendly_name = entity.get("friendly_name") or entity.get("name") or entity_id
                state = entity.get("state", "unknown")
                
                # Get relevant attributes
                attributes = entity.get("attributes", {})
                
                entity_info = {
                    "entity_id": entity_id,
                    "friendly_name": friendly_name,
                    "state": state,
                    "device_id": entity.get("device_id"),
                }
                
                # Add domain-specific attributes
                if domain == "light":
                    if "effect_list" in attributes:
                        entity_info["effect_list"] = attributes["effect_list"]
                    if "supported_color_modes" in attributes:
                        entity_info["color_modes"] = attributes["supported_color_modes"]
                    if "brightness" in attributes:
                        entity_info["brightness"] = attributes["brightness"]
                
                elif domain == "binary_sensor":
                    device_class = attributes.get("device_class", "")
                    entity_info["device_class"] = device_class
                
                area_domain_entities[area_id][domain].append(entity_info)
            
            # Format output
            parts = ["ENTITIES BY AREA:"]
            
            for area_id in sorted(area_domain_entities.keys()):
                area_name = area_name_map.get(area_id, area_id.replace("_", " ").title())
                domains = area_domain_entities[area_id]
                
                parts.append(f"\n{area_name} (area_id: {area_id}):")
                
                # Prioritize critical domains for automation
                priority_domains = ["light", "binary_sensor", "switch", "sensor", "climate", "cover"]
                sorted_domains = sorted(
                    domains.keys(),
                    key=lambda d: (priority_domains.index(d) if d in priority_domains else 99, d)
                )
                
                for domain in sorted_domains:
                    domain_entities = domains[domain]
                    parts.append(f"  {domain} ({len(domain_entities)}):")
                    
                    for entity in domain_entities[:10]:  # Limit per domain
                        entity_id = entity["entity_id"]
                        friendly_name = entity["friendly_name"]
                        state = entity["state"]
                        
                        line = f"    - {entity_id}"
                        if friendly_name and friendly_name != entity_id:
                            line += f' "{friendly_name}"'
                        line += f" (state: {state})"
                        
                        # Add device_class for binary_sensor
                        if domain == "binary_sensor" and entity.get("device_class"):
                            line += f" [device_class: {entity['device_class']}]"
                        
                        # Add effects for lights
                        if domain == "light" and entity.get("effect_list"):
                            effects = entity["effect_list"][:5]  # Top 5 effects
                            line += f" [effects: {', '.join(effects)}...]"
                        
                        parts.append(line)
                    
                    if len(domain_entities) > 10:
                        parts.append(f"    ... and {len(domain_entities) - 10} more")
            
            return "\n".join(parts)
            
        except Exception as e:
            logger.error(f"Error building area entity context: {e}", exc_info=True)
            return "ENTITY_INVENTORY: Unavailable"
    
    async def build_binary_sensor_context(self) -> str:
        """
        Build context specifically for binary sensors (motion, presence, occupancy).
        
        Critical for automation triggers based on presence/motion.
        """
        try:
            entities = await self.data_api_client.fetch_entities(limit=10000)
            if not entities:
                return "BINARY_SENSORS: No sensors found"
            
            # Fetch device registry for area resolution
            devices = await self.ha_client.get_device_registry()
            device_area_map = {
                d.get("id"): d.get("area_id")
                for d in devices if d.get("id") and d.get("area_id")
            }
            
            # Fetch areas for friendly names
            areas = await self.ha_client.get_area_registry()
            area_name_map = {
                a.get("area_id"): a.get("name", a.get("area_id", ""))
                for a in areas if a.get("area_id")
            }
            
            # Filter and group binary sensors
            sensor_by_area: dict[str, list[dict]] = defaultdict(list)
            
            for entity in entities:
                if entity.get("domain") != "binary_sensor":
                    continue
                
                entity_id = entity.get("entity_id", "")
                attributes = entity.get("attributes", {})
                device_class = attributes.get("device_class", "")
                
                # Only include motion/presence/occupancy sensors
                if device_class not in ["motion", "presence", "occupancy", "door", "window"]:
                    # Also check entity_id patterns
                    if not any(kw in entity_id.lower() for kw in ["motion", "presence", "occupancy"]):
                        continue
                
                # Resolve area
                area_id = entity.get("area_id")
                if not area_id:
                    device_id = entity.get("device_id")
                    if device_id:
                        area_id = device_area_map.get(device_id)
                area_id = area_id or "unassigned"
                
                sensor_by_area[area_id].append({
                    "entity_id": entity_id,
                    "friendly_name": entity.get("friendly_name") or entity.get("name") or entity_id,
                    "device_class": device_class,
                    "state": entity.get("state", "unknown"),
                })
            
            # Format output
            parts = ["MOTION/PRESENCE SENSORS:"]
            parts.append("(Use these for presence-based triggers)")
            parts.append("")
            
            for area_id in sorted(sensor_by_area.keys()):
                area_name = area_name_map.get(area_id, area_id.replace("_", " ").title())
                sensors = sensor_by_area[area_id]
                
                parts.append(f"{area_name}:")
                for sensor in sensors:
                    device_class = sensor["device_class"] or "motion"
                    parts.append(
                        f"  - {sensor['entity_id']} "
                        f"[{device_class}] "
                        f"(state: {sensor['state']})"
                    )
                parts.append("")
            
            if not sensor_by_area:
                parts.append("No motion/presence sensors found.")
            
            return "\n".join(parts)
            
        except Exception as e:
            logger.error(f"Error building binary sensor context: {e}", exc_info=True)
            return "BINARY_SENSORS: Unavailable"
    
    async def build_existing_automations_context(self) -> str:
        """
        Build context for existing automations (for duplicate detection).
        
        Only includes active automations (state == "on") to avoid confusion
        from disabled or unavailable automations.
        """
        try:
            # Fetch automation entities from Data API (for metadata like friendly_name)
            entities = await self.data_api_client.fetch_entities(limit=10000)
            automations = [
                e for e in entities
                if e.get("domain") == "automation"
            ]
            
            if not automations:
                return "EXISTING_AUTOMATIONS: None found"
            
            # Fetch actual states from Home Assistant
            try:
                states = await self.ha_client.get_states()
                # Create state map: entity_id -> state dict
                state_map = {
                    state.get("entity_id"): state.get("state", "unknown")
                    for state in states
                    if state.get("entity_id", "").startswith("automation.")
                }
            except Exception as e:
                logger.warning(f"Could not fetch states from Home Assistant: {e}")
                state_map = {}
            
            # Filter to only active automations and get actual state
            active_automations = []
            for auto in automations:
                entity_id = auto.get("entity_id", "")
                # Get actual state from Home Assistant (not from entity data)
                actual_state = state_map.get(entity_id, "unknown")
                
                # Only include automations that are active (state == "on")
                if actual_state == "on":
                    friendly_name = auto.get("friendly_name") or auto.get("name") or entity_id
                    active_automations.append({
                        "entity_id": entity_id,
                        "friendly_name": friendly_name,
                        "state": actual_state
                    })
            
            if not active_automations:
                return "EXISTING_AUTOMATIONS: No active automations found"
            
            parts = ["EXISTING_AUTOMATIONS:"]
            parts.append("(Check before creating to avoid duplicates)")
            parts.append("(Only active automations are shown)")
            parts.append("")
            
            for auto in active_automations[:30]:  # Limit to 30
                entity_id = auto["entity_id"]
                friendly_name = auto["friendly_name"]
                state = auto["state"]
                
                parts.append(f"  - {entity_id}: \"{friendly_name}\" (state: {state})")
            
            if len(active_automations) > 30:
                parts.append(f"  ... and {len(active_automations) - 30} more active automations")
            
            return "\n".join(parts)
            
        except Exception as e:
            logger.error(f"Error building automations context: {e}", exc_info=True)
            return "EXISTING_AUTOMATIONS: Unavailable"
    
    def build_trigger_platforms_reference(self) -> str:
        """
        Build quick reference for common trigger platforms.
        """
        return """TRIGGER PLATFORMS REFERENCE:
(Common triggers for automations)

State Change (motion/presence):
  - platform: state
    entity_id: binary_sensor.office_motion
    to: "on"  # Triggered when someone enters

State Change with Delay (leave detection):
  - platform: state
    entity_id: binary_sensor.office_motion
    to: "off"
    for: "00:05:00"  # 5 minutes of no motion

Time-based:
  - platform: time
    at: "07:00:00"
  - platform: time_pattern
    minutes: "/15"  # Every 15 minutes

Sun-based:
  - platform: sun
    event: sunset
    offset: "-00:30:00"  # 30 min before sunset
"""
    
    async def build_enhanced_context(
        self,
        user_prompt: str | None = None,
        area_ids: list[str] | None = None
    ) -> str:
        """
        Build complete enhanced context.
        
        Args:
            user_prompt: Optional user prompt to extract relevant areas
            area_ids: Optional explicit area filter
            
        Returns:
            Complete enhanced context string
        """
        # Auto-detect areas from user prompt if not specified
        if user_prompt and not area_ids:
            area_ids = self._extract_areas_from_prompt(user_prompt)
        
        parts = []
        
        # Add area-filtered entity inventory
        entity_context = await self.build_area_entity_context(area_ids)
        parts.append(entity_context)
        
        # Add binary sensors (critical for motion/presence)
        sensor_context = await self.build_binary_sensor_context()
        parts.append(sensor_context)
        
        # Add existing automations (for duplicate detection)
        automation_context = await self.build_existing_automations_context()
        parts.append(automation_context)
        
        # Add trigger platforms reference
        trigger_ref = self.build_trigger_platforms_reference()
        parts.append(trigger_ref)
        
        return "\n\n---\n\n".join(parts)
    
    def _extract_areas_from_prompt(self, user_prompt: str) -> list[str] | None:
        """
        Extract area IDs from user prompt.
        
        Args:
            user_prompt: User's natural language prompt
            
        Returns:
            List of area IDs mentioned, or None if none found
        """
        prompt_lower = user_prompt.lower()
        
        # Common area name patterns
        area_patterns = {
            "office": "office",
            "living room": "living_room",
            "bedroom": "master_bedroom",
            "master bedroom": "master_bedroom",
            "kitchen": "kitchen",
            "garage": "garage",
            "hallway": "hallway",
            "bathroom": "bathroom",
            "backyard": "backyard",
            "patio": "patio",
            "porch": "porch",
            "bar": "bar",
            "dining": "dinning_room",
            "dinning": "dinning_room",
            "laundry": "laundry_room",
            "stairs": "stairs",
        }
        
        found_areas = []
        for pattern, area_id in area_patterns.items():
            if pattern in prompt_lower:
                found_areas.append(area_id)
        
        return found_areas if found_areas else None
